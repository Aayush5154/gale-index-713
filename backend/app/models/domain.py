"""Immutable domain objects shared by the data and analysis services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ForecastRecord:
    """A single WINDFOR forecast value for one delivery hour."""

    start_time: datetime
    publish_time: datetime
    generation_mw: float
    source_index: int = 0


@dataclass(frozen=True, slots=True)
class ActualRecord:
    """A single FUELHH WIND outturn value for one half-hour settlement period."""

    start_time: datetime
    publish_time: datetime
    generation_mw: float
    settlement_date: str | None = None
    settlement_period: int | None = None
    source_index: int = 0


@dataclass(frozen=True, slots=True)
class HourlyActual:
    """Hourly average MW derived from two half-hourly FUELHH values."""

    start_time: datetime
    generation_mw: float | None
    half_hour_values: tuple[float, ...]
    expected_half_hours: int = 2

    @property
    def complete(self) -> bool:
        return len(self.half_hour_values) == self.expected_half_hours and self.generation_mw is not None


@dataclass(frozen=True, slots=True)
class ForecastSelection:
    """The outcome of reconstructing the decision-time forecast for one hour."""

    delivery_start: datetime
    cutoff: datetime
    selected: ForecastRecord | None
    eligible_count: int
    previous: ForecastRecord | None
    duplicate_publication: bool
    stale: bool

    @property
    def available(self) -> bool:
        return self.selected is not None


@dataclass
class NormalizationStats:
    received: int = 0
    valid: int = 0
    skipped_malformed: int = 0
    skipped_wrong_dataset: int = 0
    skipped_non_wind: int = 0
    skipped_invalid_timestamp: int = 0
    skipped_invalid_generation: int = 0
    skipped_unaligned: int = 0
    duplicate_exact: int = 0
    duplicate_superseded: int = 0
    ambiguous_duplicates: int = 0
    warnings: list[str] = field(default_factory=list)

    def merge(self, other: "NormalizationStats") -> None:
        self.received += other.received
        self.valid += other.valid
        self.skipped_malformed += other.skipped_malformed
        self.skipped_wrong_dataset += other.skipped_wrong_dataset
        self.skipped_non_wind += other.skipped_non_wind
        self.skipped_invalid_timestamp += other.skipped_invalid_timestamp
        self.skipped_invalid_generation += other.skipped_invalid_generation
        self.skipped_unaligned += other.skipped_unaligned
        self.duplicate_exact += other.duplicate_exact
        self.duplicate_superseded += other.duplicate_superseded
        self.ambiguous_duplicates += other.ambiguous_duplicates
        self.warnings.extend(other.warnings)

    def as_dict(self) -> dict[str, int]:
        return {
            "received": self.received,
            "valid": self.valid,
            "skipped_malformed": self.skipped_malformed,
            "skipped_wrong_dataset": self.skipped_wrong_dataset,
            "skipped_non_wind": self.skipped_non_wind,
            "skipped_invalid_timestamp": self.skipped_invalid_timestamp,
            "skipped_invalid_generation": self.skipped_invalid_generation,
            "skipped_unaligned": self.skipped_unaligned,
            "duplicate_exact": self.duplicate_exact,
            "duplicate_superseded": self.duplicate_superseded,
            "ambiguous_duplicates": self.ambiguous_duplicates,
        }
