"""Versioned, fail-closed contracts shared across Swingcut subsystems."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    """Base for strict versioned contracts."""

    model_config = ConfigDict(extra="forbid", strict=True)


class RejectionReason(StrEnum):
    NO_SWING = "no_swing"
    PRACTICE_ONLY = "practice_only"
    FALSE_START = "false_start"
    ABORTED = "aborted"
    INCOMPLETE = "incomplete"
    NO_APPARENT_STRIKE = "no_apparent_strike"
    OCCLUDED = "occluded"
    UNCERTAIN = "uncertain"


class SourceAsset(ContractModel):
    """Private source evidence. Persist only in mode-0600 run storage."""

    schema_version: int = Field(default=1, frozen=True)
    source_id: str = Field(min_length=1, max_length=512)
    source_path: Path
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_s: float = Field(gt=0)
    creation_time: datetime

    @field_validator("duration_s")
    @classmethod
    def finite_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("duration must be finite")
        return value

    @field_validator("creation_time")
    @classmethod
    def aware_creation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("creation_time must include a timezone")
        return value

    def public_summary(self) -> dict[str, object]:
        """Return only aggregate-safe facts, never source identity or path."""
        return {"schema_version": self.schema_version, "duration_s": self.duration_s}


class SwingAnalysis(ContractModel):
    """One provider candidate, before source-bound policy is applied."""

    schema_version: int = Field(default=1, frozen=True)
    candidate_id: str = Field(min_length=1, max_length=128)
    contains_apparent_ball_strike: bool
    rejection_reason: RejectionReason | None = None
    takeaway_s: float | None = Field(default=None, ge=0)
    impact_s: float | None = Field(default=None, ge=0)
    finish_s: float | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0, le=1)

    @field_validator("takeaway_s", "impact_s", "finish_s")
    @classmethod
    def finite_timeline_value(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("timeline values must be finite")
        return value

    @model_validator(mode="after")
    def coherent_classification(self) -> Self:
        timeline = (self.takeaway_s, self.impact_s, self.finish_s)
        if self.contains_apparent_ball_strike:
            if self.rejection_reason is not None:
                raise ValueError("accepted candidate cannot have a rejection reason")
            if any(value is None for value in timeline):
                raise ValueError("accepted candidate requires a complete timeline")
            takeaway, impact, finish = timeline
            assert takeaway is not None and impact is not None and finish is not None
            if not takeaway < impact < finish:
                raise ValueError("timeline must satisfy takeaway < impact < finish")
        else:
            if self.rejection_reason is None:
                raise ValueError("excluded candidate requires a rejection reason")
            if any(value is not None for value in timeline):
                raise ValueError("excluded candidate must not include timeline values")
        return self


class AnalyzedSource(ContractModel):
    """Private association between one source and its model candidates."""

    schema_version: int = Field(default=1, frozen=True)
    source_id: str = Field(min_length=1, max_length=512)
    candidates: tuple[SwingAnalysis, ...]


class EditSegment(ContractModel):
    """A deterministic render segment referencing private staged media."""

    schema_version: int = Field(default=1, frozen=True)
    source_id: str = Field(min_length=1, max_length=512)
    source_path: Path
    candidate_id: str = Field(min_length=1, max_length=128)
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    takeaway_s: float = Field(ge=0)
    impact_s: float = Field(ge=0)
    finish_s: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered_timeline(self) -> Self:
        values = (
            self.start_s,
            self.takeaway_s,
            self.impact_s,
            self.finish_s,
            self.end_s,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("segment timeline must be finite")
        if not self.start_s <= self.takeaway_s < self.impact_s < self.finish_s <= self.end_s:
            raise ValueError("segment must satisfy start <= takeaway < impact < finish <= end")
        return self


class EditPlan(ContractModel):
    schema_version: int = Field(default=1, frozen=True)
    ordering: str = Field(default="source_creation_time_then_timeline", frozen=True)
    segments: tuple[EditSegment, ...]


class RunStage(StrEnum):
    CREATED = "created"
    INVENTORY = "inventory"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    STAGING = "staging"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    RENDERING = "rendering"
    VERIFYING = "verifying"
    IMPORTING = "importing"
    CLEANUP = "cleanup"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransitionRecord(ContractModel):
    from_stage: RunStage
    to_stage: RunStage
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("transition time must include a timezone")
        return value


_ALLOWED_TRANSITIONS: dict[RunStage, frozenset[RunStage]] = {
    RunStage.CREATED: frozenset({RunStage.INVENTORY, RunStage.FAILED, RunStage.CANCELLED}),
    RunStage.INVENTORY: frozenset(
        {RunStage.AWAITING_CONFIRMATION, RunStage.FAILED, RunStage.CANCELLED}
    ),
    RunStage.AWAITING_CONFIRMATION: frozenset(
        {RunStage.STAGING, RunStage.FAILED, RunStage.CANCELLED}
    ),
    RunStage.STAGING: frozenset({RunStage.ANALYZING, RunStage.FAILED, RunStage.CANCELLED}),
    RunStage.ANALYZING: frozenset({RunStage.PLANNING, RunStage.FAILED, RunStage.CANCELLED}),
    RunStage.PLANNING: frozenset(
        {RunStage.RENDERING, RunStage.CLEANUP, RunStage.FAILED, RunStage.CANCELLED}
    ),
    RunStage.RENDERING: frozenset({RunStage.VERIFYING, RunStage.FAILED, RunStage.CANCELLED}),
    RunStage.VERIFYING: frozenset({RunStage.IMPORTING, RunStage.FAILED, RunStage.CANCELLED}),
    RunStage.IMPORTING: frozenset({RunStage.CLEANUP, RunStage.FAILED}),
    RunStage.CLEANUP: frozenset({RunStage.SUCCEEDED, RunStage.FAILED}),
    RunStage.SUCCEEDED: frozenset(),
    RunStage.FAILED: frozenset(),
    RunStage.CANCELLED: frozenset(),
}


class RunState(ContractModel):
    """Durable state machine. Forward transitions cannot skip confirmation."""

    schema_version: int = Field(default=1, frozen=True)
    run_id: str = Field(min_length=1, max_length=128)
    stage: RunStage = RunStage.CREATED
    transitions: tuple[TransitionRecord, ...] = ()

    @model_validator(mode="after")
    def valid_history(self) -> Self:
        expected = RunStage.CREATED
        for transition in self.transitions:
            if transition.from_stage is not expected:
                raise ValueError("run transition history is not contiguous")
            if transition.to_stage not in _ALLOWED_TRANSITIONS[expected]:
                raise ValueError("run transition history contains an invalid transition")
            expected = transition.to_stage
        if self.stage is not expected:
            raise ValueError("current run stage does not match transition history")
        return self

    def transition(self, destination: RunStage, *, at: datetime | None = None) -> RunState:
        if (
            not isinstance(destination, RunStage)
            or destination not in _ALLOWED_TRANSITIONS[self.stage]
        ):
            raise ValueError(f"invalid run transition: {self.stage} -> {destination}")
        occurred_at = at or datetime.now(UTC)
        record = TransitionRecord(
            from_stage=self.stage,
            to_stage=destination,
            occurred_at=occurred_at,
        )
        return RunState(
            run_id=self.run_id,
            stage=destination,
            transitions=(*self.transitions, record),
        )

    def public_summary(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "stage": self.stage.value,
        }


class RunManifest(ContractModel):
    """Privacy-safe retained manifest; source identities and paths cannot be represented."""

    schema_version: int = Field(default=1, frozen=True)
    run_id: str = Field(min_length=1, max_length=128)
    state: RunStage
    source_count: int = Field(ge=0)
    source_duration_s: float = Field(ge=0)
    accepted_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    failed_source_count: int = Field(ge=0)
    proxy_profile_version: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    analysis_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validator_version: str = Field(min_length=1, max_length=128)
    output_profile: str | None = Field(default=None, max_length=128)

    @field_validator("source_duration_s")
    @classmethod
    def finite_source_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("source duration must be finite")
        return value

    @model_validator(mode="after")
    def count_consistency(self) -> Self:
        if self.failed_source_count > self.source_count:
            raise ValueError("failed source count cannot exceed source count")
        return self


class EventType(StrEnum):
    STATUS = "status"
    PROGRESS = "progress"
    WARNING = "warning"
    COMPLETE = "complete"
    ERROR = "error"


class EventMessage(StrEnum):
    INVENTORY_STARTED = "inventory_started"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    STAGING_MEDIA = "staging_media"
    ANALYZING_MEDIA = "analyzing_media"
    PLANNING_EDIT = "planning_edit"
    RENDERING_OUTPUT = "rendering_output"
    VERIFYING_OUTPUT = "verifying_output"
    IMPORTING_OUTPUT = "importing_output"
    CLEANING_UP = "cleaning_up"
    RUN_SUCCEEDED = "run_succeeded"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    SOURCE_EXCLUDED = "source_excluded"
    NO_CONFIDENT_SWINGS = "no_confident_swings"


class NoticeCode(StrEnum):
    SOURCE_FAILURE = "source_failure"
    NO_CONFIDENT_SWINGS = "no_confident_swings"
    PERMISSION_DENIED = "permission_denied"
    COST_ESTIMATE_UNAVAILABLE = "cost_estimate_unavailable"
    MALFORMED_ANALYSIS = "malformed_analysis"
    OUTPUT_VERIFICATION_FAILED = "output_verification_failed"
    IMPORT_FAILED = "import_failed"
    CANCELLED = "cancelled"


class RunEvent(ContractModel):
    """Bounded JSONL event safe for Pi conversation display."""

    schema_version: int = Field(default=1, frozen=True)
    event: EventType
    run_id: str = Field(min_length=1, max_length=128)
    stage: RunStage
    message: EventMessage
    completed: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)
    notice_code: NoticeCode | None = None
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def aware_event_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event time must include a timezone")
        return value

    @model_validator(mode="after")
    def progress_consistency(self) -> Self:
        if (self.completed is None) != (self.total is None):
            raise ValueError("completed and total must be supplied together")
        if self.completed is not None and self.total is not None and self.completed > self.total:
            raise ValueError("completed cannot exceed total")
        needs_notice = self.event in {EventType.WARNING, EventType.ERROR}
        if needs_notice and self.notice_code is None:
            raise ValueError("warning and error events require notice_code")
        if not needs_notice and self.notice_code is not None:
            raise ValueError("notice_code is only valid for warning and error events")
        return self
