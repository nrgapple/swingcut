"""Policy-pinned Gemini Interactions adapter with strict privacy and spend gates."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, Decimal
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from swingcut.contracts import AnalyzedSource, ContractModel, SwingAnalysis
from swingcut.media.proxy import ProxyArtifact, ProxyGenerationError, verify_cloud_proxy
from swingcut.providers.base import (
    AnalysisProvider,
    AnalysisResult,
    CostCapError,
    DeletionDebtError,
    MalformedProviderOutputError,
    ProviderError,
    SpendBudget,
    UnsupportedCapabilityError,
    UsageRecord,
    finite_nonnegative_int,
)


@dataclass(frozen=True)
class ModelPolicy:
    """Reviewed capability and pricing required before a model can be selected."""

    model: str
    pricing_valid_through: date
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal


DEFAULT_MODEL = "gemini-3.7-flash"
MODEL_POLICIES = {
    DEFAULT_MODEL: ModelPolicy(
        model=DEFAULT_MODEL,
        pricing_valid_through=date(2026, 12, 31),
        input_usd_per_million=Decimal("0.75"),
        output_usd_per_million=Decimal("3.75"),
    )
}
PROMPT_VERSION = "swing-analysis-v1"
MAX_ATTEMPTS = 2
MAX_OUTPUT_TOKENS = 4096
REQUEST_TIMEOUT_S = 180.0
# Static high-resolution video is documented at 258 tokens/s. Agentic is normally
# cheaper; 4x plus a 4096-token prompt allowance is a deliberately conservative bound.
VIDEO_INPUT_TOKENS_PER_SECOND = 258
AGENTIC_INPUT_MULTIPLIER = 4
PROMPT_INPUT_TOKEN_ALLOWANCE = 4096

PROMPT = """Identify every candidate golf swing in this video. Include a candidate only when
an apparent ball strike is visually supported. Reject practice-only, false-start, aborted,
incomplete, occluded, no-apparent-strike, no-swing, and uncertain events rather than guessing.
For accepted candidates report takeaway, impact, and finish times in seconds from video start.
For rejected candidates provide no timestamps. Return only the requested JSON object.
"""


class _AnalysisEnvelope(ContractModel):
    schema_version: int = 1
    candidates: tuple[SwingAnalysis, ...]


RESPONSE_SCHEMA = _AnalysisEnvelope.model_json_schema()
RESPONSE_SCHEMA["required"] = ["schema_version", "candidates"]
RESPONSE_SCHEMA["properties"]["schema_version"] = {"const": 1, "type": "integer"}
_candidate_schema = RESPONSE_SCHEMA["$defs"]["SwingAnalysis"]
_candidate_schema["required"] = [
    "schema_version",
    "candidate_id",
    "contains_apparent_ball_strike",
    "rejection_reason",
    "takeaway_s",
    "impact_s",
    "finish_s",
    "confidence",
]
_candidate_schema["properties"]["schema_version"] = {"const": 1, "type": "integer"}
PROMPT_SHA256 = hashlib.sha256(PROMPT.encode()).hexdigest()
SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(RESPONSE_SCHEMA, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


class GeminiProvider(AnalysisProvider):
    """Pinned Interactions API adapter. The SDK client is injectable for routine mocks."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any | None = None,
        model: str = DEFAULT_MODEL,
        today: date | None = None,
        sleep: Callable[[float], None] = time.sleep,
        proxy_verifier: Callable[[ProxyArtifact], None] = verify_cloud_proxy,
    ) -> None:
        try:
            self.model_policy = MODEL_POLICIES[model]
        except KeyError as error:
            raise UnsupportedCapabilityError("Gemini model has no reviewed policy") from error
        self._today = today or date.today()
        self._assert_current_pricing()
        self._sleep = sleep
        self._verify_proxy = proxy_verifier
        if client is None:
            if not api_key:
                raise ValueError("Gemini API key is required")
            http_options = types.HttpOptions(
                timeout=int(REQUEST_TIMEOUT_S * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            )
            client = genai.Client(api_key=api_key, http_options=http_options)
        self._client = client

    def estimate_run_cost_for_durations(self, durations_s: tuple[float, ...]) -> Decimal:
        self._assert_current_pricing()
        total = sum(
            (self._attempt_cost_for_duration(duration) for duration in durations_s), Decimal("0")
        )
        estimate = total * MAX_ATTEMPTS
        if estimate > Decimal("1.00"):
            raise CostCapError("conservative Gemini estimate exceeds the US$1 run cap")
        return estimate

    def estimate_run_cost(self, proxies: tuple[ProxyArtifact, ...]) -> Decimal:
        return self.estimate_run_cost_for_durations(tuple(proxy.duration_s for proxy in proxies))

    def analyze(
        self, proxy: ProxyArtifact, *, source_id: str, budget: SpendBudget
    ) -> AnalysisResult:
        self._assert_current_pricing()
        if not isinstance(proxy, ProxyArtifact):
            raise MalformedProviderOutputError("provider accepts only a typed proxy artifact")
        try:
            self._verify_proxy(proxy)
        except (OSError, ValueError, ProxyGenerationError) as error:
            raise MalformedProviderOutputError("cloud proxy verification failed") from error
        if not source_id or len(source_id) > 512:
            raise ValueError("source_id must be non-empty and bounded")

        attempt_cost = self._attempt_cost(proxy)
        upload_name: str | None = None
        upload_created = False
        deletion_error: Exception | None = None
        result: AnalysisResult | None = None
        primary_error: Exception | None = None
        try:
            uploaded = self._client.files.upload(
                file=proxy.path,
                config={"mime_type": "video/mp4", "display_name": "swingcut-proxy"},
            )
            upload_created = True
            upload_name = self._required_string(uploaded, "name")
            upload_uri = self._required_string(uploaded, "uri")
            usage_records: list[UsageRecord] = []
            response: Any | None = None
            for attempt in range(1, MAX_ATTEMPTS + 1):
                budget.authorize(attempt_cost)
                try:
                    response = self._create_interaction(upload_uri)
                except Exception as error:
                    if attempt == MAX_ATTEMPTS or not _is_retryable(error):
                        raise
                    self._sleep(0.25 * (2 ** (attempt - 1)))
                    continue
                record = self._usage_record(response, attempt, attempt_cost)
                budget.reconcile(attempt_cost, record.actual_cost_usd)
                usage_records.append(record)
                break
            if response is None:
                raise MalformedProviderOutputError("Gemini returned no interaction")
            analysis = self._validate_response(response, source_id, proxy.duration_s)
            result = AnalysisResult(analysis=analysis, usage=tuple(usage_records))
        except Exception as error:
            primary_error = error
        finally:
            if upload_name is not None:
                deletion_error = self._delete_upload(upload_name)
            elif upload_created:
                deletion_error = DeletionDebtError("Gemini upload omitted its deletion name")

        if deletion_error is not None:
            raise DeletionDebtError(
                "Gemini upload deletion failed after bounded retries"
            ) from deletion_error
        if primary_error is not None:
            if isinstance(primary_error, ProviderError):
                raise primary_error
            raise MalformedProviderOutputError("Gemini interaction failed") from primary_error
        assert result is not None
        return result

    def _create_interaction(self, upload_uri: str) -> Any:
        return self._client.interactions.create(
            model=self.model_policy.model,
            input=[
                {"type": "text", "text": PROMPT},
                {
                    "type": "video",
                    "uri": upload_uri,
                    "mime_type": "video/mp4",
                    "processing": "agentic",
                },
            ],
            generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": RESPONSE_SCHEMA,
            },
            store=False,
            timeout=REQUEST_TIMEOUT_S,
        )

    def _validate_response(
        self, response: Any, source_id: str, duration_s: float
    ) -> AnalyzedSource:
        if _field(response, "status") != "completed":
            raise MalformedProviderOutputError("Gemini interaction did not complete")
        response_model = _field(response, "model")
        if (
            response_model is not None
            and str(response_model).removeprefix("models/") != self.model_policy.model
        ):
            raise UnsupportedCapabilityError("Gemini returned an unpinned model")
        steps = _field(response, "steps")
        if not isinstance(steps, list):
            raise UnsupportedCapabilityError("Gemini returned no processing evidence")
        calls = {
            str(_field(step, "id")) for step in steps if _field(step, "type") == "processing_call"
        }
        results = {
            str(_field(step, "call_id"))
            for step in steps
            if _field(step, "type") == "processing_result"
        }
        if not calls or not calls.issubset(results):
            raise UnsupportedCapabilityError("agentic processing evidence is incomplete")
        output = _field(response, "output_text")
        if not isinstance(output, str) or not output:
            raise MalformedProviderOutputError("Gemini returned no structured output")
        try:
            payload = json.loads(output)
            _require_exact_response_fields(payload)
            payload["candidates"] = tuple(payload["candidates"])
            envelope = _AnalysisEnvelope.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            raise MalformedProviderOutputError(
                "Gemini returned malformed structured output"
            ) from error
        ids = [candidate.candidate_id for candidate in envelope.candidates]
        if len(ids) != len(set(ids)):
            raise MalformedProviderOutputError("Gemini returned duplicate candidate identifiers")
        for candidate in envelope.candidates:
            if candidate.finish_s is not None and candidate.finish_s > duration_s:
                raise MalformedProviderOutputError("Gemini returned an out-of-bounds timeline")
        return AnalyzedSource(source_id=source_id, candidates=envelope.candidates)

    def _usage_record(self, response: Any, attempt: int, estimate: Decimal) -> UsageRecord:
        usage = _field(response, "usage")
        if usage is None:
            raise MalformedProviderOutputError("Gemini returned no usage record")
        input_tokens = finite_nonnegative_int(
            _field(usage, "total_input_tokens"), field="total_input_tokens"
        )
        output_tokens = finite_nonnegative_int(
            _field(usage, "total_output_tokens"), field="total_output_tokens"
        )
        thought_tokens = finite_nonnegative_int(
            _field(usage, "total_thought_tokens") or 0, field="total_thought_tokens"
        )
        tool_tokens = finite_nonnegative_int(
            _field(usage, "total_tool_use_tokens") or 0, field="total_tool_use_tokens"
        )
        actual = _token_cost(
            input_tokens,
            output_tokens + thought_tokens + tool_tokens,
            policy=self.model_policy,
        )
        return UsageRecord(
            model=self.model_policy.model,
            attempt=attempt,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thought_tokens=thought_tokens,
            tool_use_tokens=tool_tokens,
            estimated_cost_usd=estimate,
            actual_cost_usd=actual,
        )

    def _attempt_cost(self, proxy: ProxyArtifact) -> Decimal:
        return self._attempt_cost_for_duration(proxy.duration_s)

    def _attempt_cost_for_duration(self, duration_s: float) -> Decimal:
        if duration_s <= 0:
            raise ValueError("proxy duration must be positive")
        input_tokens = (
            int(duration_s * VIDEO_INPUT_TOKENS_PER_SECOND * AGENTIC_INPUT_MULTIPLIER)
            + PROMPT_INPUT_TOKEN_ALLOWANCE
        )
        return _token_cost(input_tokens, MAX_OUTPUT_TOKENS, policy=self.model_policy)

    def _delete_upload(self, name: str) -> Exception | None:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self._client.files.delete(name=name)
                return None
            except Exception as error:
                last_error = error
                if attempt < 2:
                    self._sleep(0.25 * (2**attempt))
        return last_error

    def _assert_current_pricing(self) -> None:
        if self._today > self.model_policy.pricing_valid_through:
            raise CostCapError("Gemini pricing snapshot has expired")

    @staticmethod
    def _required_string(owner: Any, name: str) -> str:
        value = _field(owner, name)
        if not isinstance(value, str) or not value:
            raise MalformedProviderOutputError(f"Gemini upload omitted {name}")
        return value


def _require_exact_response_fields(payload: object) -> None:
    root_fields = {"schema_version", "candidates"}
    candidate_fields = {
        "schema_version",
        "candidate_id",
        "contains_apparent_ball_strike",
        "rejection_reason",
        "takeaway_s",
        "impact_s",
        "finish_s",
        "confidence",
    }
    if not isinstance(payload, dict) or set(payload) != root_fields:
        raise ValueError("analysis response fields do not match the contract")
    if payload.get("schema_version") != 1 or not isinstance(payload.get("candidates"), list):
        raise ValueError("analysis response root is invalid")
    for candidate in payload["candidates"]:
        if not isinstance(candidate, dict) or set(candidate) != candidate_fields:
            raise ValueError("candidate fields do not match the contract")
        if candidate.get("schema_version") != 1:
            raise ValueError("candidate schema version is invalid")


def _field(owner: Any, name: str) -> Any:
    if isinstance(owner, dict):
        return owner.get(name)
    return getattr(owner, name, None)


def _token_cost(input_tokens: int, output_tokens: int, *, policy: ModelPolicy) -> Decimal:
    cost = (
        Decimal(input_tokens) * policy.input_usd_per_million
        + Decimal(output_tokens) * policy.output_usd_per_million
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True
    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    return isinstance(status, int) and (status in {408, 429} or 500 <= status <= 599)
