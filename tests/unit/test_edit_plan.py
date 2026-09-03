from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from swingcut.contracts import AnalyzedSource, RejectionReason, SourceAsset, SwingAnalysis
from swingcut.planning.edit_plan import ExclusionReason, PlanningError, build_edit_plan

NOW = datetime(2026, 9, 2, 12, tzinfo=UTC)


def source(source_id: str, duration: float, created: datetime) -> SourceAsset:
    return SourceAsset(
        source_id=source_id,
        source_path=Path(f"/private/{source_id}.mov"),
        content_sha256="a" * 64,
        duration_s=duration,
        creation_time=created,
    )


def accepted(
    candidate_id: str,
    takeaway: float,
    impact: float,
    finish: float,
    confidence: float = 0.95,
) -> SwingAnalysis:
    return SwingAnalysis(
        candidate_id=candidate_id,
        contains_apparent_ball_strike=True,
        takeaway_s=takeaway,
        impact_s=impact,
        finish_s=finish,
        confidence=confidence,
    )


def test_plan_pads_to_source_bounds_and_orders_by_creation_then_timeline() -> None:
    newer = source("newer", 20.0, NOW + timedelta(hours=1))
    older = source("older", 10.0, NOW)
    analyses = (
        AnalyzedSource(source_id="newer", candidates=(accepted("c3", 5, 6, 7),)),
        AnalyzedSource(
            source_id="older",
            candidates=(accepted("c2", 6, 7, 9), accepted("c1", 1, 2, 3)),
        ),
    )

    result = build_edit_plan((newer, older), analyses)

    assert [segment.candidate_id for segment in result.plan.segments] == ["c1", "c2", "c3"]
    first, second, _ = result.plan.segments
    assert first.start_s == 0
    assert first.end_s == 6
    assert second.start_s == 4
    assert second.end_s == 10
    assert result.exclusions.total == 0


def test_plan_strictly_excludes_rejected_low_confidence_and_out_of_bounds() -> None:
    asset = source("asset", 12.0, NOW)
    analysis = AnalyzedSource(
        source_id="asset",
        candidates=(
            SwingAnalysis(
                candidate_id="uncertain",
                contains_apparent_ball_strike=False,
                rejection_reason=RejectionReason.UNCERTAIN,
                confidence=0.99,
            ),
            accepted("low", 1, 2, 3, confidence=0.89),
            accepted("outside", 8, 10, 13),
            accepted("good", 4, 5, 6),
        ),
    )

    result = build_edit_plan((asset,), (analysis,))

    assert [segment.candidate_id for segment in result.plan.segments] == ["good"]
    assert result.exclusions.total == 3
    assert result.exclusions.by_reason == {
        ExclusionReason.PROVIDER_REJECTED: 1,
        ExclusionReason.BELOW_CONFIDENCE: 1,
        ExclusionReason.OUT_OF_BOUNDS: 1,
    }


def test_plan_excludes_duplicate_and_overlapping_detections() -> None:
    asset = source("asset", 20.0, NOW)
    analysis = AnalyzedSource(
        source_id="asset",
        candidates=(
            accepted("first", 2, 3, 5),
            accepted("overlap", 4, 5, 7),
            accepted("first", 10, 11, 12),
        ),
    )

    result = build_edit_plan((asset,), (analysis,))

    assert [segment.candidate_id for segment in result.plan.segments] == ["first"]
    assert result.exclusions.by_reason == {
        ExclusionReason.DUPLICATE_CANDIDATE: 1,
        ExclusionReason.OVERLAPPING_CANDIDATE: 1,
    }


def test_plan_rejects_unknown_or_duplicate_source_associations() -> None:
    asset = source("asset", 20.0, NOW)
    unknown = AnalyzedSource(source_id="other", candidates=())
    with pytest.raises(PlanningError, match="outside the selected inventory"):
        build_edit_plan((asset,), (unknown,))

    with pytest.raises(PlanningError, match="duplicate source"):
        build_edit_plan((asset, asset), ())
