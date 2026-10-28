"""Response schemas for the analysis endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import (
    CoverageSummary,
    DataFreshness,
    QuerySummary,
    UtcDatetime,
)


class IntervalBase(BaseModel):
    delivery_start_utc: UtcDatetime
    delivery_start_local: str
    delivery_date_local: date
    cutoff_utc: UtcDatetime
    cutoff_local: str
    status: str
    forecast_mw: float | None = None
    forecast_publication_utc: UtcDatetime | None = None
    forecast_publication_local: str | None = None
    lead_time_hours: float | None = None
    eligible_forecast_count: int
    duplicate_publication: bool
    stale_forecast: bool
    previous_publication_utc: UtcDatetime | None = None
    previous_forecast_mw: float | None = None


class ForecastInterval(IntervalBase):
    pass


class ComparisonInterval(IntervalBase):
    actual_mw: float | None = None
    actual_half_hours: int
    signed_error_mw: float | None = None
    absolute_error_mw: float | None = None
    squared_error_mw2: float | None = None
    absolute_percentage_error: float | None = None


class HalfHourActual(BaseModel):
    start_utc: UtcDatetime
    start_local: str
    generation_mw: float
    settlement_date: str | None = None
    settlement_period: int | None = None


class ForecastSummary(BaseModel):
    expected_intervals: int
    available: int
    missing: int
    coverage_percent: float
    distinct_publications: int
    publication_min_utc: UtcDatetime | None = None
    publication_min_local: str | None = None
    publication_max_utc: UtcDatetime | None = None
    publication_max_local: str | None = None
    lead_time_min_hours: float | None = None
    lead_time_max_hours: float | None = None
    duplicate_publication_intervals: int
    stale_intervals: int


class ForecastResponse(BaseModel):
    query: QuerySummary
    summary: ForecastSummary
    intervals: list[ForecastInterval]
    data_source: DataFreshness
    warnings: list[str]
    data_quality: dict[str, object]


class ComparisonResponse(BaseModel):
    query: QuerySummary
    coverage: CoverageSummary
    intervals: list[ComparisonInterval]
    half_hourly_actuals: list[HalfHourActual]
    data_source: DataFreshness
    warnings: list[str]
    data_quality: dict[str, object]


class AccuracyMetricsModel(BaseModel):
    mae_mw: float | None = None
    rmse_mw: float | None = None
    mbe_mw: float | None = None
    mape_percent: float | None = None
    mape_valid_count: int
    mape_excluded_count: int
    max_abs_error_mw: float | None = None
    max_abs_error_at_utc: UtcDatetime | None = None
    max_abs_error_at_local: str | None = None


class DecisionContext(BaseModel):
    mode: str
    timezone: str
    cutoff_time_local: str
    first_cutoff_utc: UtcDatetime
    first_cutoff_local: str
    last_cutoff_utc: UtcDatetime
    last_cutoff_local: str
    fixed_cutoff_utc: UtcDatetime | None = None
    fixed_cutoff_local: str | None = None
    rule: str
    distinct_publications: int
    earliest_publication_utc: UtcDatetime | None = None
    latest_publication_utc: UtcDatetime | None = None
    lead_time_min_hours: float | None = None
    lead_time_max_hours: float | None = None


class HistogramBinModel(BaseModel):
    lower_mw: float
    upper_mw: float
    count: int
    signed_side: str


class ErrorHistogramModel(BaseModel):
    bin_width_mw: float
    total_pairs: int
    bins: list[HistogramBinModel]


class MetricsResponse(BaseModel):
    query: QuerySummary
    coverage: CoverageSummary
    metrics: AccuracyMetricsModel
    decision_context: DecisionContext
    histogram: ErrorHistogramModel
    data_source: DataFreshness
    warnings: list[str]
    data_quality: dict[str, object]


class DailyMetricModel(BaseModel):
    date: date
    expected_intervals: int
    forecast_available: int
    valid_pairs: int
    missing_forecast: int
    missing_actual: int
    missing_both: int
    coverage_percent: float
    valid_pair_percent: float
    mae_mw: float | None = None
    rmse_mw: float | None = None
    mbe_mw: float | None = None
    mape_percent: float | None = None
    mape_valid_count: int
    mape_excluded_count: int
    max_abs_error_mw: float | None = None


class DailyMetricsResponse(BaseModel):
    query: QuerySummary
    coverage: CoverageSummary
    daily: list[DailyMetricModel]
    warnings: list[str] = Field(default_factory=list)
