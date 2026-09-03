from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from swingcut.contracts import (
    EventMessage,
    EventType,
    RejectionReason,
    RunEvent,
    RunManifest,
    RunStage,
    RunState,
    SourceAsset,
    SwingAnalysis,
)

NOW = datetime(2026, 9, 2, 12, tzinfo=UTC)
HASH = "a" * 64


def test_analysis_accepts_strict_ordered_timeline() -> None:
    analysis = SwingAnalysis(
        candidate_id="candidate-1",
        contains_apparent_ball_strike=True,
        takeaway_s=3.0,
        impact_s=4.0,
        finish_s=5.5,
        confidence=0.96,
    )
    assert analysis.finish_s == 5.5


@pytest.mark.parametrize(
    ("takeaway", "impact", "finish"),
    [(3.0, 3.0, 4.0), (4.0, 3.0, 5.0), (2.0, 5.0, 4.0)],
)
def test_analysis_rejects_invalid_timeline(takeaway: float, impact: float, finish: float) -> None:
    with pytest.raises(ValidationError, match="takeaway < impact < finish"):
        SwingAnalysis(
            candidate_id="candidate-1",
            contains_apparent_ball_strike=True,
            takeaway_s=takeaway,
            impact_s=impact,
            finish_s=finish,
            confidence=0.99,
        )


def test_analysis_rejects_non_finite_and_incomplete_timeline() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        SwingAnalysis(
            candidate_id="candidate-1",
            contains_apparent_ball_strike=True,
            takeaway_s=1.0,
            impact_s=2.0,
            finish_s=float("nan"),
            confidence=0.99,
        )
    with pytest.raises(ValidationError, match="complete timeline"):
        SwingAnalysis(
            candidate_id="candidate-1",
            contains_apparent_ball_strike=True,
            takeaway_s=1.0,
            impact_s=2.0,
            confidence=0.99,
        )


def test_excluded_analysis_requires_reason_and_no_timeline() -> None:
    excluded = SwingAnalysis(
        candidate_id="candidate-1",
        contains_apparent_ball_strike=False,
        rejection_reason=RejectionReason.UNCERTAIN,
        confidence=0.6,
    )
    assert excluded.rejection_reason is RejectionReason.UNCERTAIN

    with pytest.raises(ValidationError, match="must not include timeline"):
        SwingAnalysis(
            candidate_id="candidate-1",
            contains_apparent_ball_strike=False,
            rejection_reason=RejectionReason.PRACTICE_ONLY,
            takeaway_s=1.0,
            confidence=0.3,
        )


def test_source_public_summary_redacts_private_values() -> None:
    source = SourceAsset(
        source_id="photos-local-identifier/private",
        source_path=Path("/private/run/IMG_1234.mov"),
        content_sha256=HASH,
        duration_s=12.5,
        creation_time=NOW,
    )
    rendered = str(source.public_summary())
    assert source.public_summary() == {"schema_version": 1, "duration_s": 12.5}
    assert "photos-local" not in rendered
    assert "IMG_1234" not in rendered
    assert HASH not in rendered


def test_run_state_enforces_confirmation_and_terminal_transitions() -> None:
    state = RunState(run_id="run-1")
    state = state.transition(RunStage.INVENTORY, at=NOW)
    state = state.transition(RunStage.AWAITING_CONFIRMATION, at=NOW)
    state = state.transition(RunStage.STAGING, at=NOW)
    assert state.stage is RunStage.STAGING
    assert len(state.transitions) == 3

    with pytest.raises(ValueError, match="invalid run transition"):
        RunState(run_id="run-2").transition(RunStage.STAGING, at=NOW)

    cancelled = RunState(run_id="run-3").transition(RunStage.CANCELLED, at=NOW)
    with pytest.raises(ValueError, match="invalid run transition"):
        cancelled.transition(RunStage.INVENTORY, at=NOW)

    with pytest.raises(ValidationError, match="does not match transition history"):
        RunState(run_id="run-4", stage=RunStage.RENDERING)


def test_manifest_cannot_hold_sensitive_fields() -> None:
    fields: dict[str, object] = {
        "run_id": "run-1",
        "state": RunStage.PLANNING,
        "source_count": 2,
        "source_duration_s": 30.0,
        "accepted_count": 1,
        "excluded_count": 1,
        "failed_source_count": 0,
        "proxy_profile_version": "proxy-v1",
        "model_version": "gemini-version",
        "prompt_sha256": HASH,
        "analysis_schema_sha256": "b" * 64,
        "validator_version": "validator-v1",
    }
    manifest = RunManifest(**fields)
    payload = manifest.model_dump_json()
    assert "source_id" not in payload
    assert "source_path" not in payload

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RunManifest(**fields, source_path="/private/video.mov")


def test_public_json_schemas_match_contract_models() -> None:
    schema_dir = Path(__file__).parents[2] / "schemas"
    for filename, model in (
        ("run-event-v1.schema.json", RunEvent),
        ("run-manifest-v1.schema.json", RunManifest),
    ):
        assert json.loads((schema_dir / filename).read_text()) == model.model_json_schema()


def test_event_json_is_bounded_and_has_no_arbitrary_private_payload() -> None:
    event = RunEvent(
        event=EventType.PROGRESS,
        run_id="run-1",
        stage=RunStage.ANALYZING,
        message=EventMessage.ANALYZING_MEDIA,
        completed=1,
        total=2,
        occurred_at=NOW,
    )
    payload = event.model_dump_json()
    assert '"event":"progress"' in payload

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RunEvent(
            event=EventType.STATUS,
            run_id="run-1",
            stage=RunStage.INVENTORY,
            message=EventMessage.INVENTORY_STARTED,
            occurred_at=NOW,
            source_path="/private/video.mov",
        )

    with pytest.raises(ValidationError, match="completed cannot exceed total"):
        RunEvent(
            event=EventType.PROGRESS,
            run_id="run-1",
            stage=RunStage.ANALYZING,
            message=EventMessage.ANALYZING_MEDIA,
            completed=3,
            total=2,
            occurred_at=NOW,
        )

    with pytest.raises(ValidationError):
        RunEvent(
            event=EventType.STATUS,
            run_id="run-1",
            stage=RunStage.INVENTORY,
            message="private filename IMG_1234.mov",
            occurred_at=NOW,
        )
