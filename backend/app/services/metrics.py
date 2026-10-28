"""Accuracy metrics, coverage statistics and daily summaries.

Metrics are calculated only from valid forecast/actual pairs.  Forecast
availability is reported separately and is never called accuracy.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from app.models.domain import NormalizationStats
from app.services.comparison import ComparisonRow


@dataclass(frozen=True)
class CoverageStats:
    expected_intervals: int
    forecast_available: int
    missing_forecast: int
    valid_pairs: int
    missing_actual: int
    missing_both: int
    coverage_percent: float
    valid_pair_percent: float
    status_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AccuracyMetrics:
    mae_mw: float | None
    rmse_mw: float | None
    mbe_mw: float | None
    mape_percent: float | None
    mape_valid_count: int
    mape_excluded_count: int
    max_abs_error_mw: float | None
    max_abs_error_at: datetime | None


@dataclass(frozen=True)
class DailyMetrics:
    day: date
    expected_intervals: int
    forecast_available: int
    valid_pairs: int
    missing_forecast: int
    missing_actual: int
    missing_both: int
    coverage_percent: float
    valid_pair_percent: float
    mae_mw: float | None
    rmse_mw: float | None
    mbe_mw: float | None
    mape_percent: float | None
    mape_valid_count: int
    mape_excluded_count: int
    max_abs_error_mw: float | None


@dataclass(frozen=True)
class HistogramBin:
    lower_mw: float
    upper_mw: float
    count: int
    signed_side: str


@dataclass(frozen=True)
class ErrorHistogram:
    bin_width_mw: float
    bins: list[HistogramBin]
    total_pairs: int


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 4) if denominator else 0.0


def compute_coverage(rows: list[ComparisonRow]) -> CoverageStats:
    expected = len(rows)
    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[row.status] += 1

    matched = status_counts["matched"]
    missing_actual_only = status_counts["missing_actual"]
    missing_both = status_counts["missing_both"]
    forecast_available = matched + missing_actual_only
    missing_forecast = expected - forecast_available
    missing_actual = missing_actual_only + missing_both

    return CoverageStats(
        expected_intervals=expected,
        forecast_available=forecast_available,
        missing_forecast=missing_forecast,
        valid_pairs=matched,
        missing_actual=missing_actual,
        missing_both=missing_both,
        coverage_percent=_percent(forecast_available, expected),
        valid_pair_percent=_percent(matched, expected),
        status_counts=dict(status_counts),
    )


def compute_accuracy(rows: list[ComparisonRow]) -> AccuracyMetrics:
    pairs = [row for row in rows if row.is_valid_pair]
    if not pairs:
        return AccuracyMetrics(
            mae_mw=None,
            rmse_mw=None,
            mbe_mw=None,
            mape_percent=None,
            mape_valid_count=0,
            mape_excluded_count=0,
            max_abs_error_mw=None,
            max_abs_error_at=None,
        )

    signed = [row.signed_error_mw for row in pairs if row.signed_error_mw is not None]
    absolute = [abs(value) for value in signed]
    squared = [value * value for value in signed]
    pct_values = [row.absolute_percentage_error for row in pairs if row.absolute_percentage_error is not None]

    max_abs = max(absolute)
    max_row = next(row for row in pairs if row.absolute_error_mw == max_abs)

    return AccuracyMetrics(
        mae_mw=round(sum(absolute) / len(absolute), 4),
        rmse_mw=round(math.sqrt(sum(squared) / len(squared)), 4),
        mbe_mw=round(sum(signed) / len(signed), 4),
        mape_percent=round(sum(pct_values) / len(pct_values), 4) if pct_values else None,
        mape_valid_count=len(pct_values),
        mape_excluded_count=len(pairs) - len(pct_values),
        max_abs_error_mw=round(max_abs, 4),
        max_abs_error_at=max_row.delivery_start,
    )


def _group_by_local_day(
    rows: list[ComparisonRow], tz: ZoneInfo
) -> list[tuple[date, list[ComparisonRow]]]:
    """Group comparison rows by their London delivery date.

    Pandas handles the timezone conversion so that DST transition days stay
    grouped by the local calendar date rather than by a fixed UTC offset.
    """
    if not rows:
        return []

    frame = pd.DataFrame({"delivery_start": [row.delivery_start for row in rows]})
    frame["day"] = frame["delivery_start"].dt.tz_convert(tz).dt.date
    return [
        (day, [rows[int(index)] for index in group.index])
        for day, group in frame.groupby("day", sort=True)
    ]


def compute_daily(rows: list[ComparisonRow], tz: ZoneInfo) -> list[DailyMetrics]:
    daily: list[DailyMetrics] = []
    for day, day_rows in _group_by_local_day(rows, tz):
        coverage = compute_coverage(day_rows)
        accuracy = compute_accuracy(day_rows)
        daily.append(
            DailyMetrics(
                day=day,
                expected_intervals=coverage.expected_intervals,
                forecast_available=coverage.forecast_available,
                valid_pairs=coverage.valid_pairs,
                missing_forecast=coverage.missing_forecast,
                missing_actual=coverage.missing_actual,
                missing_both=coverage.missing_both,
                coverage_percent=coverage.coverage_percent,
                valid_pair_percent=coverage.valid_pair_percent,
                mae_mw=accuracy.mae_mw,
                rmse_mw=accuracy.rmse_mw,
                mbe_mw=accuracy.mbe_mw,
                mape_percent=accuracy.mape_percent,
                mape_valid_count=accuracy.mape_valid_count,
                mape_excluded_count=accuracy.mape_excluded_count,
                max_abs_error_mw=accuracy.max_abs_error_mw,
            )
        )
    return daily


def _nice_bin_width(span: float, target_bins: int = 12) -> float:
    if span <= 0 or not math.isfinite(span):
        return 1.0
    raw = span / target_bins
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiplier in (1, 2, 2.5, 5, 10):
        width = multiplier * magnitude
        if raw <= width:
            return max(width, 0.1)
    return max(10 * magnitude, 0.1)


def compute_error_histogram(rows: list[ComparisonRow]) -> ErrorHistogram:
    errors = [row.signed_error_mw for row in rows if row.signed_error_mw is not None]
    if not errors:
        return ErrorHistogram(bin_width_mw=0.0, bins=[], total_pairs=0)

    span = max(errors) - min(errors)
    width = _nice_bin_width(span)
    lower = min(math.floor(min(errors) / width) * width, 0.0)
    upper = max(math.ceil(max(errors) / width) * width, 0.0)
    if upper <= lower:
        upper = lower + width

    bin_count = max(1, int(round((upper - lower) / width)))
    counts = [0] * bin_count
    for value in errors:
        index = int((value - lower) / width)
        index = min(max(index, 0), bin_count - 1)
        counts[index] += 1

    bins: list[HistogramBin] = []
    for index, count in enumerate(counts):
        bin_lower = lower + index * width
        bin_upper = bin_lower + width
        if bin_lower >= 0:
            side = "overforecast"
        elif bin_upper <= 0:
            side = "underforecast"
        else:
            side = "straddles_zero"
        bins.append(
            HistogramBin(
                lower_mw=round(bin_lower, 2),
                upper_mw=round(bin_upper, 2),
                count=count,
                signed_side=side,
            )
        )

    return ErrorHistogram(bin_width_mw=round(width, 4), bins=bins, total_pairs=len(errors))


def build_warnings(
    *,
    rows: list[ComparisonRow],
    coverage: CoverageStats,
    accuracy: AccuracyMetrics,
    actual_stats: NormalizationStats,
    forecast_stats: NormalizationStats,
    incomplete_hours: int,
    coverage_threshold: float = 95.0,
) -> list[str]:
    warnings: list[str] = []

    if coverage.missing_forecast:
        warnings.append(
            f"{coverage.missing_forecast} of {coverage.expected_intervals} hourly intervals "
            "have no eligible forecast at the configured cut-off. They are excluded from error metrics."
        )
    if coverage.missing_actual:
        warnings.append(
            f"{coverage.missing_actual} hourly intervals have incomplete or missing FUELHH outturn."
        )
    if coverage.expected_intervals and coverage.coverage_percent < coverage_threshold:
        warnings.append(
            f"Forecast coverage is {coverage.coverage_percent:.1f}%, below the "
            f"{coverage_threshold:.0f}% review threshold. Treat aggregate metrics with caution."
        )
    if accuracy.mape_valid_count and accuracy.mape_excluded_count:
        warnings.append(
            f"MAPE excludes {accuracy.mape_excluded_count} pair(s) where the actual value was below "
            "the configured minimum denominator; MAE, RMSE and MBE still include them."
        )
    if any(row.selection.duplicate_publication for row in rows):
        warnings.append(
            "One or more delivery hours had multiple eligible forecasts with the same publication "
            "time; a deterministic highest-generation tie-break was applied and flagged."
        )
    if any(row.selection.stale for row in rows):
        warnings.append(
            "One or more selected forecasts were published more than the configured staleness "
            "threshold before delivery."
        )
    if actual_stats.ambiguous_duplicates:
        warnings.append(
            f"{actual_stats.ambiguous_duplicates} FUELHH interval(s) had conflicting records at the "
            "same publication time; the higher value was selected and the ambiguity counted."
        )
    if actual_stats.skipped_non_wind or forecast_stats.skipped_wrong_dataset:
        pass  # Filtering is expected; a non-WIND row is not a quality warning on its own.
    if actual_stats.skipped_invalid_generation or forecast_stats.skipped_invalid_generation:
        warnings.append(
            "Some source records had missing, non-numeric or negative generation values and were excluded."
        )
    if incomplete_hours:
        warnings.append(
            f"{incomplete_hours} hourly interval(s) did not have both half-hourly FUELHH readings "
            "and were treated as missing actuals."
        )
    return warnings
