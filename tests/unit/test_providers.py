from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from swingcut.media.proxy import PROXY_PROFILE_VERSION, ProxyArtifact
from swingcut.providers.base import (
    CostCapError,
    DeletionDebtError,
    MalformedProviderOutputError,
    SpendBudget,
    UnsupportedCapabilityError,
)
from swingcut.providers.gemini import MAX_ATTEMPTS, MODEL, GeminiProvider


class RetryableError(RuntimeError):
    status_code = 503


class FakeFiles:
    def __init__(
        self,
        *,
        delete_errors: list[Exception] | None = None,
        upload_result: Any | None = None,
    ) -> None:
        self.upload_calls: list[dict[str, Any]] = []
        self.delete_calls: list[str] = []
        self.delete_errors = list(delete_errors or [])
        self.upload_result = upload_result or SimpleNamespace(
            name="files/mock", uri="https://provider.invalid/files/mock"
        )

    def upload(self, **kwargs: Any) -> Any:
        self.upload_calls.append(kwargs)
        return self.upload_result

    def delete(self, *, name: str) -> None:
        self.delete_calls.append(name)
        if self.delete_errors:
            raise self.delete_errors.pop(0)


class FakeInteractions:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(
        self,
        responses: list[Any],
        *,
        delete_errors: list[Exception] | None = None,
        upload_result: Any | None = None,
    ) -> None:
        self.files = FakeFiles(delete_errors=delete_errors, upload_result=upload_result)
        self.interactions = FakeInteractions(responses)


def _artifact(tmp_path: Path, *, duration_s: float = 10.0, sanitized: bool = True) -> ProxyArtifact:
    path = tmp_path / "proxy.mp4"
    path.write_bytes(b"synthetic sanitized proxy")
    return ProxyArtifact(
        path=path,
        source_sha256="a" * 64,
        proxy_sha256="b" * 64,
        duration_s=duration_s,
        width=480,
        height=270,
        frame_rate=15.0,
        sanitizer_verified=sanitized,
    )


def _candidate(*, finish_s: float = 4.0) -> dict[str, object]:
    return {
        "schema_version": 1,
        "candidate_id": "candidate-1",
        "contains_apparent_ball_strike": True,
        "rejection_reason": None,
        "takeaway_s": 1.0,
        "impact_s": 2.0,
        "finish_s": finish_s,
        "confidence": 0.95,
    }


def _response(
    *,
    output: str | None = None,
    steps: list[dict[str, str]] | None = None,
    usage: dict[str, int] | None = None,
    status: str = "completed",
    model: str = MODEL,
) -> dict[str, object]:
    return {
        "status": status,
        "model": model,
        "steps": steps
        if steps is not None
        else [
            {"type": "processing_call", "id": "process-1"},
            {"type": "processing_result", "call_id": "process-1"},
            {"type": "model_output"},
        ],
        "output_text": output
        if output is not None
        else json.dumps({"schema_version": 1, "candidates": [_candidate()]}),
        "usage": usage
        if usage is not None
        else {
            "total_input_tokens": 1000,
            "total_output_tokens": 100,
            "total_thought_tokens": 50,
            "total_tool_use_tokens": 25,
        },
    }


def _provider(client: FakeClient, **kwargs: Any) -> GeminiProvider:
    return GeminiProvider(
        client=client,
        today=date(2026, 9, 4),
        sleep=lambda _: None,
        proxy_verifier=kwargs.pop("proxy_verifier", lambda _: None),
        **kwargs,
    )


def test_success_enforces_agentic_schema_usage_and_cleanup(tmp_path: Path) -> None:
    client = FakeClient([_response()])
    provider = _provider(client)
    budget = SpendBudget()

    result = provider.analyze(_artifact(tmp_path), source_id="private-source", budget=budget)

    assert result.analysis.source_id == "private-source"
    assert result.analysis.candidates[0].impact_s == 2.0
    assert result.uploaded_file_deleted is True
    assert len(result.usage) == 1
    assert result.usage[0].actual_cost_usd > 0
    assert budget.spent_usd == result.usage[0].actual_cost_usd
    assert client.files.delete_calls == ["files/mock"]
    request = client.interactions.calls[0]
    assert request["model"] == MODEL
    assert request["input"][1]["processing"] == "agentic"
    assert request["response_format"]["mime_type"] == "application/json"
    assert request["store"] is False
    assert request["timeout"] == 180.0
    assert "private-source" not in json.dumps(request)


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (_response(output="not-json"), MalformedProviderOutputError),
        (
            _response(
                output=json.dumps(
                    {
                        "schema_version": 1,
                        "candidates": [
                            {key: value for key, value in _candidate().items() if key != "impact_s"}
                        ],
                    }
                )
            ),
            MalformedProviderOutputError,
        ),
        (_response(steps=[]), UnsupportedCapabilityError),
        (
            _response(steps=[{"type": "processing_call", "id": "unmatched"}]),
            UnsupportedCapabilityError,
        ),
        (_response(status="failed"), MalformedProviderOutputError),
        (_response(model="gemini-other"), UnsupportedCapabilityError),
        (
            _response(
                output=json.dumps({"schema_version": 1, "candidates": [_candidate(finish_s=11)]})
            ),
            MalformedProviderOutputError,
        ),
        (
            _response(
                output=json.dumps({"schema_version": 1, "candidates": [_candidate(), _candidate()]})
            ),
            MalformedProviderOutputError,
        ),
    ],
)
def test_response_failures_still_delete_upload(
    tmp_path: Path, response: dict[str, object], error: type[Exception]
) -> None:
    client = FakeClient([response])
    with pytest.raises(error):
        _provider(client).analyze(_artifact(tmp_path), source_id="source", budget=SpendBudget())
    assert client.files.delete_calls == ["files/mock"]


def test_missing_or_invalid_usage_fails_closed_and_deletes(tmp_path: Path) -> None:
    for usage in (None, {"total_input_tokens": -1, "total_output_tokens": 1}):
        response = _response()
        response["usage"] = usage
        client = FakeClient([response])
        with pytest.raises(MalformedProviderOutputError):
            _provider(client).analyze(_artifact(tmp_path), source_id="source", budget=SpendBudget())
        assert client.files.delete_calls == ["files/mock"]


def test_retry_is_bounded_costed_and_only_for_transient_errors(tmp_path: Path) -> None:
    client = FakeClient([RetryableError("temporary"), _response()])
    budget = SpendBudget()
    result = _provider(client).analyze(_artifact(tmp_path), source_id="source", budget=budget)
    assert len(client.interactions.calls) == MAX_ATTEMPTS
    assert budget.spent_usd > result.usage[0].actual_cost_usd

    client = FakeClient([RuntimeError("permanent"), _response()])
    with pytest.raises(MalformedProviderOutputError):
        _provider(client).analyze(_artifact(tmp_path), source_id="source", budget=SpendBudget())
    assert len(client.interactions.calls) == 1
    assert client.files.delete_calls == ["files/mock"]


def test_budget_refuses_before_interaction_and_estimate_refuses_large_run(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    client = FakeClient([_response()])
    budget = SpendBudget(Decimal("0.000001"))
    with pytest.raises(CostCapError):
        _provider(client).analyze(artifact, source_id="source", budget=budget)
    assert client.interactions.calls == []
    assert client.files.delete_calls == ["files/mock"]

    huge = artifact.model_copy(update={"duration_s": 10_000.0})
    with pytest.raises(CostCapError):
        _provider(FakeClient([])).estimate_run_cost((huge,))


def test_expired_pricing_fails_before_client_use() -> None:
    with pytest.raises(CostCapError, match="expired"):
        GeminiProvider(client=FakeClient([]), today=date(2027, 1, 1))


def test_original_path_is_rejected_without_upload(tmp_path: Path) -> None:
    client = FakeClient([])
    provider = _provider(client)
    with pytest.raises(MalformedProviderOutputError, match="typed proxy"):
        provider.analyze(  # type: ignore[arg-type]
            tmp_path / "original.mov", source_id="source", budget=SpendBudget()
        )
    assert client.files.upload_calls == []


def test_unverified_artifact_is_rejected_without_upload(tmp_path: Path) -> None:
    client = FakeClient([])
    provider = GeminiProvider(client=client, today=date(2026, 9, 4), sleep=lambda _: None)
    with pytest.raises(MalformedProviderOutputError, match="proxy verification"):
        provider.analyze(
            _artifact(tmp_path, sanitized=False), source_id="source", budget=SpendBudget()
        )
    assert client.files.upload_calls == []


def test_untrackable_upload_is_deletion_debt(tmp_path: Path) -> None:
    client = FakeClient([], upload_result=SimpleNamespace(uri="https://provider.invalid/file"))
    with pytest.raises(DeletionDebtError):
        _provider(client).analyze(_artifact(tmp_path), source_id="source", budget=SpendBudget())
    assert client.interactions.calls == []


def test_deletion_debt_overrides_success_after_three_attempts(tmp_path: Path) -> None:
    client = FakeClient([_response()], delete_errors=[RuntimeError("delete") for _ in range(3)])
    with pytest.raises(DeletionDebtError):
        _provider(client).analyze(_artifact(tmp_path), source_id="source", budget=SpendBudget())
    assert client.files.delete_calls == ["files/mock"] * 3


def test_proxy_profile_is_pinned(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path).model_copy(update={"profile_version": "broader-profile"})
    assert artifact.profile_version != PROXY_PROFILE_VERSION
    client = FakeClient([])
    provider = GeminiProvider(client=client, today=date(2026, 9, 4), sleep=lambda _: None)
    with pytest.raises(MalformedProviderOutputError):
        provider.analyze(artifact, source_id="source", budget=SpendBudget())
    assert client.files.upload_calls == []
