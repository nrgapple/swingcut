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

USD_ONE = Decimal("1.00")


class ProviderError(RuntimeError):
    """An external analysis provider failed closed."""


class CostCapError(ProviderError):
    """A request cannot be conservatively kept within the run cap."""


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


class SpendBudget:
    """Thread-safe per-run ledger that authorizes every potentially billable attempt."""

    def __init__(self, cap_usd: Decimal = USD_ONE, *, spent_usd: Decimal = Decimal("0")) -> None:
        if not cap_usd.is_finite() or cap_usd <= 0 or cap_usd > USD_ONE:
            raise ValueError("spend cap must be finite, positive, and no more than US$1")
        if not spent_usd.is_finite() or spent_usd < 0 or spent_usd > cap_usd:
            raise ValueError("prior spend must be finite and within the run cap")
        self.cap_usd = cap_usd
        self.spent_usd = spent_usd
        self._lock = Lock()

    @property
    def remaining_usd(self) -> Decimal:
        with self._lock:
            return self.cap_usd - self.spent_usd

    def authorize(self, worst_case_usd: Decimal) -> None:
        if not worst_case_usd.is_finite() or worst_case_usd <= 0:
            raise ValueError("attempt estimate must be finite and positive")
        with self._lock:
            if self.spent_usd + worst_case_usd > self.cap_usd:
                raise CostCapError("provider attempt would exceed the US$1 run cap")
            # Charge before the call. A failed call has unknown usage and keeps this charge.
            self.spent_usd += worst_case_usd

    def reconcile(self, worst_case_usd: Decimal, actual_usd: Decimal) -> None:
        if not actual_usd.is_finite() or actual_usd < 0 or actual_usd > worst_case_usd:
            raise CostCapError("returned usage cannot be conservatively reconciled")
        with self._lock:
            self.spent_usd -= worst_case_usd - actual_usd


class AnalysisProvider(ABC):
    @abstractmethod
    def estimate_run_cost_for_durations(self, durations_s: tuple[float, ...]) -> Decimal:
        """Estimate before staging so confirmation can precede paid or mutating work."""

    @abstractmethod
    def estimate_run_cost(self, proxies: tuple[ProxyArtifact, ...]) -> Decimal:
        """Recheck the retry-inclusive estimate from verified proxies before upload."""

    @abstractmethod
    def analyze(
        self, proxy: ProxyArtifact, *, source_id: str, budget: SpendBudget
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
