"""Provider-neutral analysis, spend, usage, and cleanup contracts."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from decimal import Decimal
from threading import Lock
from typing import Self

from pydantic import Field, model_validator

from swingcut.contracts import AnalyzedSource, ContractModel
from swingcut.media.proxy import ProxyArtifact


class ProviderError(RuntimeError):
    """An external analysis provider failed closed."""


class CostEstimateError(ProviderError):
    """A required provider cost estimate cannot be calculated reliably."""


class ProviderInteractionError(ProviderError):
    """A provider request failed with a privacy-safe transport/status category."""


class MalformedProviderOutputError(ProviderError):
    """Provider output or processing evidence was absent or malformed."""


class UnsupportedCapabilityError(ProviderError):
    """The pinned model did not perform a required operation."""


class DeletionDebtError(ProviderError):
    """At least one cloud upload could not be deleted immediately."""


class UsageRecord(ContractModel):
    """Bounded billable usage retained without provider prose or media identity."""

    model: str = Field(min_length=1, max_length=128)
    attempt: int = Field(ge=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    thought_tokens: int = Field(ge=0)
    tool_use_tokens: int = Field(ge=0)
    estimated_cost_usd: Decimal = Field(ge=0)
    actual_cost_usd: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def finite_costs(self) -> Self:
        if not self.estimated_cost_usd.is_finite() or not self.actual_cost_usd.is_finite():
            raise ValueError("usage costs must be finite")
        return self


class AnalysisResult(ContractModel):
    analysis: AnalyzedSource
    usage: tuple[UsageRecord, ...]
    uploaded_file_deleted: bool = Field(default=True, frozen=True)


class UsageLedger:
    """Thread-safe cumulative accounting without treating an estimate as a hard maximum."""

    def __init__(self, *, accounted_usd: Decimal = Decimal("0")) -> None:
        if not accounted_usd.is_finite() or accounted_usd < 0:
            raise ValueError("prior accounted usage must be finite and nonnegative")
        self.accounted_usd = accounted_usd
        self._lock = Lock()

    def record_attempt(self, estimated_usd: Decimal) -> None:
        """Record the estimate before a potentially billable attempt.

        Failed attempts retain this conservative amount because actual usage is unknown.
        """
        if not estimated_usd.is_finite() or estimated_usd <= 0:
            raise ValueError("attempt estimate must be finite and positive")
        with self._lock:
            self.accounted_usd += estimated_usd

    def record_actual(self, estimated_usd: Decimal, actual_usd: Decimal) -> None:
        """Replace a successful attempt's estimate with returned usage, even when higher."""
        if not estimated_usd.is_finite() or estimated_usd <= 0:
            raise ValueError("attempt estimate must be finite and positive")
        if not actual_usd.is_finite() or actual_usd < 0:
            raise ValueError("returned usage cost must be finite and nonnegative")
        with self._lock:
            self.accounted_usd += actual_usd - estimated_usd


class AnalysisProvider(ABC):
    @abstractmethod
    def estimate_run_cost_for_durations(self, durations_s: tuple[float, ...]) -> Decimal:
        """Estimate before staging so confirmation can precede paid or mutating work."""

    @abstractmethod
    def estimate_run_cost(self, proxies: tuple[ProxyArtifact, ...]) -> Decimal:
        """Recheck the retry-inclusive estimate from verified proxies before upload."""

    @abstractmethod
    def analyze(
        self, proxy: ProxyArtifact, *, source_id: str, ledger: UsageLedger
    ) -> AnalysisResult:
        """Analyze exactly one verified cloud proxy."""


def finite_nonnegative_int(value: object, *, field: str) -> int:
    """Strictly normalize provider token counters."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MalformedProviderOutputError(f"invalid provider usage field: {field}")
    return value


def finite_duration(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("proxy duration must be finite and positive")
    return value
