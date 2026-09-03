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
    CostEstimateError,
    DeletionDebtError,
    MalformedProviderOutputError,
    ProviderError,
    ProviderInteractionError,
    UnsupportedCapabilityError,
    UsageLedger,
    UsageRecord,
    finite_nonnegative_int,
)


@dataclass(frozen=True)
class ModelPolicy:
    """Reviewed capability and pricing required before a model can be selected."""

    model: str
    api: str
    pricing_valid_through: date
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    video_input_multiplier: int


DEFAULT_MODEL = "gemini-3.7-flash"
FALLBACK_MODEL = "gemini-3.5-flash"
ANALYSIS_POLICY_VERSION = "gemini-3.7-interactions+gemini-3.5-generate-429-fallback-v1"
MODEL_POLICIES = {
    DEFAULT_MODEL: ModelPolicy(
        model=DEFAULT_MODEL,
        api="interactions",
        pricing_valid_through=date(2026, 12, 31),
        input_usd_per_million=Decimal("0.75"),
        output_usd_per_million=Decimal("3.75"),
        video_input_multiplier=4,
    ),
    FALLBACK_MODEL: ModelPolicy(
        model=FALLBACK_MODEL,
        api="generate-content",
        pricing_valid_through=date(2026, 12, 31),
        input_usd_per_million=Decimal("1.50"),
        output_usd_per_million=Decimal("9.00"),
        video_input_multiplier=1,
    ),
}
PROMPT_VERSION = "swing-analysis-v1"
MAX_ATTEMPTS = 2
MAX_OUTPUT_TOKENS = 4096
REQUEST_TIMEOUT_S = 600.0
# Static high-resolution video is documented at 258 tokens/s. The reviewed primary
# policy uses a conservative 4x agentic multiplier; fallback uses the documented rate.
VIDEO_INPUT_TOKENS_PER_SECOND = 258
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
        fallback_model: str = FALLBACK_MODEL,
        today: date | None = None,
        sleep: Callable[[float], None] = time.sleep,
        proxy_verifier: Callable[[ProxyArtifact], None] = verify_cloud_proxy,
    ) -> None:
        try:
            self.model_policy = MODEL_POLICIES[model]
            self.fallback_policy = MODEL_POLICIES[fallback_model]
        except KeyError as error:
            raise UnsupportedCapabilityError("Gemini model has no reviewed policy") from error
        if (
            self.model_policy.api != "interactions"
            or self.fallback_policy.api != "generate-content"
        ):
            raise UnsupportedCapabilityError("Gemini primary/fallback API policy is invalid")
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

    @property
    def pricing_valid_through(self) -> date:
        return min(
            self.model_policy.pricing_valid_through,
            self.fallback_policy.pricing_valid_through,
        )

    def estimate_run_cost_for_durations(self, durations_s: tuple[float, ...]) -> Decimal:
        self._assert_current_pricing()
        policies = (self.model_policy, self.fallback_policy)
        total = sum(
            (
                self._attempt_cost_for_duration(duration, policy)
                for duration in durations_s
                for policy in policies
            ),
            Decimal("0"),
        )
        return total * MAX_ATTEMPTS

    def estimate_run_cost(self, proxies: tuple[ProxyArtifact, ...]) -> Decimal:
        return self.estimate_run_cost_for_durations(tuple(proxy.duration_s for proxy in proxies))

    def analyze(
        self, proxy: ProxyArtifact, *, source_id: str, ledger: UsageLedger
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
            try:
                response, usage = self._request_with_retries(
                    lambda: self._create_interaction(upload_uri),
                    proxy,
                    self.model_policy,
                    ledger,
                )
                analysis = self._validate_response(response, source_id, proxy.duration_s)
            except Exception as error:
                if _status_code(error) != 429:
                    raise
                response, usage = self._request_with_retries(
                    lambda: self._create_fallback(upload_uri),
                    proxy,
                    self.fallback_policy,
                    ledger,
                )
                analysis = self._validate_fallback_response(response, source_id, proxy.duration_s)
            result = AnalysisResult(analysis=analysis, usage=(usage,))
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
            raise ProviderInteractionError(
                f"Gemini interaction failed ({_failure_category(primary_error)})"
            ) from primary_error
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

    def _create_fallback(self, upload_uri: str) -> Any:
        return self._client.models.generate_content(
            model=self.fallback_policy.model,
            contents=[
                PROMPT,
                types.File(uri=upload_uri, mime_type="video/mp4"),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=RESPONSE_SCHEMA,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.1,
            ),
        )

    def _request_with_retries(
        self,
        request: Callable[[], Any],
        proxy: ProxyArtifact,
        policy: ModelPolicy,
        ledger: UsageLedger,
    ) -> tuple[Any, UsageRecord]:
        attempt_cost = self._attempt_cost(proxy, policy)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            ledger.record_attempt(attempt_cost)
            try:
                response = request()
            except Exception as error:
                if attempt == MAX_ATTEMPTS or not _is_retryable(error):
                    raise
                self._sleep(0.25 * (2 ** (attempt - 1)))
                continue
            record = self._usage_record(response, attempt, attempt_cost, policy)
            ledger.record_actual(attempt_cost, record.actual_cost_usd)
            return response, record
        raise AssertionError("bounded request loop did not return or raise")

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
        return self._parse_analysis(output, source_id, duration_s)

    def _validate_fallback_response(
        self, response: Any, source_id: str, duration_s: float
    ) -> AnalyzedSource:
        response_model = _field(response, "model_version")
        if (
            response_model is not None
            and str(response_model).removeprefix("models/") != self.fallback_policy.model
        ):
            raise UnsupportedCapabilityError("Gemini returned an unpinned fallback model")
        return self._parse_analysis(_field(response, "text"), source_id, duration_s)

    def _parse_analysis(self, output: Any, source_id: str, duration_s: float) -> AnalyzedSource:
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

    def _usage_record(
        self,
        response: Any,
        attempt: int,
        estimate: Decimal,
        policy: ModelPolicy,
    ) -> UsageRecord:
        if policy.api == "interactions":
            usage = _field(response, "usage")
            fields = (
                "total_input_tokens",
                "total_output_tokens",
                "total_thought_tokens",
                "total_tool_use_tokens",
            )
        else:
            usage = _field(response, "usage_metadata")
            fields = (
                "prompt_token_count",
                "candidates_token_count",
                "thoughts_token_count",
                "tool_use_prompt_token_count",
            )
        if usage is None:
            raise MalformedProviderOutputError("Gemini returned no usage record")
        input_value = _field(usage, fields[0])
        output_value = _field(usage, fields[1])
        if policy.api == "generate-content" and (input_value is None or output_value is None):
            # Some successful GenerateContent responses report only total usage.
            # Charge every token at the higher output rate rather than undercount.
            input_tokens = 0
            output_tokens = finite_nonnegative_int(
                _field(usage, "total_token_count"), field="total_token_count"
            )
            thought_tokens = 0
            tool_tokens = 0
        else:
            input_tokens = finite_nonnegative_int(input_value, field=fields[0])
            output_tokens = finite_nonnegative_int(output_value, field=fields[1])
            thought_tokens = finite_nonnegative_int(_field(usage, fields[2]) or 0, field=fields[2])
            tool_tokens = finite_nonnegative_int(_field(usage, fields[3]) or 0, field=fields[3])
        actual = _token_cost(
            input_tokens,
            output_tokens + thought_tokens + tool_tokens,
            policy=policy,
        )
        return UsageRecord(
            model=policy.model,
            attempt=attempt,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thought_tokens=thought_tokens,
            tool_use_tokens=tool_tokens,
            estimated_cost_usd=estimate,
            actual_cost_usd=actual,
        )

    def _attempt_cost(self, proxy: ProxyArtifact, policy: ModelPolicy) -> Decimal:
        return self._attempt_cost_for_duration(proxy.duration_s, policy)

    def _attempt_cost_for_duration(self, duration_s: float, policy: ModelPolicy) -> Decimal:
        if duration_s <= 0:
            raise ValueError("proxy duration must be positive")
        input_tokens = (
            int(duration_s * VIDEO_INPUT_TOKENS_PER_SECOND * policy.video_input_multiplier)
            + PROMPT_INPUT_TOKEN_ALLOWANCE
        )
        return _token_cost(input_tokens, MAX_OUTPUT_TOKENS, policy=policy)

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
        if any(
            self._today > policy.pricing_valid_through
            for policy in (self.model_policy, self.fallback_policy)
        ):
            raise CostEstimateError("Gemini pricing snapshot has expired")

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


def _status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    return status if isinstance(status, int) else None


def _failure_category(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ConnectionError):
        return "connection"
    status = _status_code(error)
    return f"http-{status}" if status is not None else "provider-error"


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True
    status = _status_code(error)
    return status is not None and (status in {408, 429} or 500 <= status <= 599)
