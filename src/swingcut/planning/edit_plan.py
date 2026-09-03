"""Deterministic policy gate between probabilistic analysis and rendering."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum

from pydantic import Field

from swingcut.contracts import (
    AnalyzedSource,
    ContractModel,
    EditPlan,
    EditSegment,
    SourceAsset,
)

TAKEAWAY_PADDING_S = 2.0
FINISH_PADDING_S = 3.0
MINIMUM_CONFIDENCE = 0.90


class ExclusionReason(StrEnum):
    PROVIDER_REJECTED = "provider_rejected"
    BELOW_CONFIDENCE = "below_confidence"
    OUT_OF_BOUNDS = "out_of_bounds"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    OVERLAPPING_CANDIDATE = "overlapping_candidate"


class ExclusionSummary(ContractModel):
    """Aggregate-only report safe to retain and show to the user."""

    total: int = Field(ge=0)
    by_reason: dict[ExclusionReason, int]


class PlanningResult(ContractModel):
    plan: EditPlan
    exclusions: ExclusionSummary


class PlanningError(ValueError):
    """Analysis cannot be safely associated with the private source inventory."""


def build_edit_plan(
    sources: tuple[SourceAsset, ...],
    analyses: tuple[AnalyzedSource, ...],
    *,
    minimum_confidence: float = MINIMUM_CONFIDENCE,
) -> PlanningResult:
    """Apply strict eligibility policy and produce a source-ordered edit plan."""
    if not 0 <= minimum_confidence <= 1:
        raise ValueError("minimum_confidence must be between zero and one")

    source_by_id = _unique_by_source_id(sources, "source inventory")
    analysis_by_id = _unique_by_source_id(analyses, "analysis set")
    unknown = analysis_by_id.keys() - source_by_id.keys()
    if unknown:
        raise PlanningError("analysis references a source outside the selected inventory")

    exclusions: Counter[ExclusionReason] = Counter()
    sortable_segments: list[tuple[object, float, str, EditSegment]] = []

    for source_id, analysis in analysis_by_id.items():
        source = source_by_id[source_id]
        accepted_ranges: list[tuple[float, float]] = []
        candidate_ids: set[str] = set()

        for candidate in sorted(
            analysis.candidates,
            key=lambda item: (
                item.takeaway_s if item.takeaway_s is not None else float("inf"),
                item.candidate_id,
            ),
        ):
            if candidate.candidate_id in candidate_ids:
                exclusions[ExclusionReason.DUPLICATE_CANDIDATE] += 1
                continue
            candidate_ids.add(candidate.candidate_id)

            if not candidate.contains_apparent_ball_strike:
                exclusions[ExclusionReason.PROVIDER_REJECTED] += 1
                continue
            if candidate.confidence < minimum_confidence:
                exclusions[ExclusionReason.BELOW_CONFIDENCE] += 1
                continue

            assert candidate.takeaway_s is not None
            assert candidate.impact_s is not None
            assert candidate.finish_s is not None
            if candidate.finish_s > source.duration_s:
                exclusions[ExclusionReason.OUT_OF_BOUNDS] += 1
                continue
            if any(
                candidate.takeaway_s < prior_finish and candidate.finish_s > prior_takeaway
                for prior_takeaway, prior_finish in accepted_ranges
            ):
                exclusions[ExclusionReason.OVERLAPPING_CANDIDATE] += 1
                continue

            accepted_ranges.append((candidate.takeaway_s, candidate.finish_s))
            segment = EditSegment(
                source_id=source.source_id,
                source_path=source.source_path,
                candidate_id=candidate.candidate_id,
                start_s=max(0.0, candidate.takeaway_s - TAKEAWAY_PADDING_S),
                end_s=min(source.duration_s, candidate.finish_s + FINISH_PADDING_S),
                takeaway_s=candidate.takeaway_s,
                impact_s=candidate.impact_s,
                finish_s=candidate.finish_s,
            )
            sortable_segments.append(
                (source.creation_time, candidate.takeaway_s, source.source_id, segment)
            )

    segments = tuple(item[3] for item in sorted(sortable_segments, key=lambda item: item[:3]))
    by_reason = {reason: exclusions[reason] for reason in ExclusionReason if exclusions[reason]}
    return PlanningResult(
        plan=EditPlan(segments=segments),
        exclusions=ExclusionSummary(total=sum(exclusions.values()), by_reason=by_reason),
    )


def _unique_by_source_id[T: SourceAsset | AnalyzedSource](
    items: tuple[T, ...], description: str
) -> dict[str, T]:
    result: dict[str, T] = {}
    for item in items:
        if item.source_id in result:
            raise PlanningError(f"duplicate source in {description}")
        result[item.source_id] = item
    return result
