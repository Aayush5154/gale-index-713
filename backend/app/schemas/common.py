"""Shared response schema building blocks."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, Field, PlainSerializer


def _serialize_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


UtcDatetime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc, return_type=str, when_used="json"),
]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Period(BaseModel):
    from_date: date
    to_date: date


class QuerySummary(BaseModel):
    from_date: date
    to_date: date
    timezone: str
    cutoff_mode: str
    cutoff_time_local: str
    cutoff_datetime_utc: UtcDatetime | None = None
    cutoff_datetime_local: str | None = None
    delivery_start_utc: UtcDatetime
    delivery_end_utc: UtcDatetime
    delivery_start_local: str
    delivery_end_local: str
    expected_intervals: int
    resolution: str


class CoverageSummary(BaseModel):
    expected_intervals: int
    forecast_available: int
    missing_forecast: int
    valid_pairs: int
    missing_actual: int
    missing_both: int
    coverage_percent: float
    valid_pair_percent: float
    status_counts: dict[str, int] = Field(default_factory=dict)


class DataFreshness(BaseModel):
    data_mode: str
    is_synthetic: bool
    source_name: str
    generated_at_utc: UtcDatetime
    cache_ttl_seconds: int
    cache: dict[str, int]
    fetch: dict[str, int]


class MetricDefinition(BaseModel):
    key: str
    label: str
    formula: str
    unit: str
    interpretation: str


class DatasetField(BaseModel):
    name: str
    description: str


class DatasetInfo(BaseModel):
    key: str
    name: str
    description: str
    endpoint: str
    documentation_url: str
    resolution: str
    fields: list[DatasetField]


class DataQualityRule(BaseModel):
    topic: str
    handling: str


class CutoffInfo(BaseModel):
    default_mode: str
    default_time_local: str
    timezone: str
    rule: str
    reference: str
    reference_url: str
    alternatives: list[str]


class ResolutionInfo(BaseModel):
    forecast: str
    actual: str
    comparison: str
    explanation: str


class UnitsInfo(BaseModel):
    generation: str
    energy: str
    note: str


class MetadataResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    data_mode: str
    is_synthetic: bool
    timezone: str
    generated_at_utc: UtcDatetime
    target_period: Period
    supported_range: Period | None
    supported_range_note: str
    max_range_days: int
    cutoff: CutoffInfo
    resolution: ResolutionInfo
    units: UnitsInfo
    datasets: list[DatasetInfo]
    metric_definitions: list[MetricDefinition]
    data_quality_rules: list[DataQualityRule]
    limitations: list[str]


class DependencyStatus(BaseModel):
    name: str
    configured: bool
    status: str
    last_success_at: str | None = None
    last_error: str | None = None
    last_error_at: str | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    data_mode: str
    is_synthetic: bool
    timezone: str
    timestamp_utc: UtcDatetime
    dependencies: list[DependencyStatus]
    cache: dict[str, int]
