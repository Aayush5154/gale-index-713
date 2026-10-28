"""Mapping from domain results to API response models."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from app.models.domain import ForecastSelection
from app.schemas.common import CoverageSummary, DataFreshness, QuerySummary
from app.schemas.responses import (
    AccuracyMetricsModel,
    ComparisonInterval,
    ComparisonResponse,
    DailyMetricModel,
    DailyMetricsResponse,
    DecisionContext,
    ErrorHistogramModel,
    ForecastInterval,
    ForecastResponse,
    ForecastSummary,
    HalfHourActual,
    HistogramBinModel,
    MetricsResponse,
)
from app.services.analysis import AnalysisBundle, AnalysisService
from app.services.comparison import ComparisonRow
from app.services.metrics import (
    AccuracyMetrics,
    CoverageStats,
    DailyMetrics,
    ErrorHistogram,
)
from app.services.timeutils import to_local_iso


def _zone(bundle: AnalysisBundle) -> ZoneInfo:
    return ZoneInfo(bundle.query.timezone_name)


def _round(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


def query_summary(service: AnalysisService, bundle: AnalysisBundle) -> QuerySummary:
    data = service.query_summary(bundle)
    return QuerySummary(**data)


def coverage_summary(coverage: CoverageStats) -> CoverageSummary:
    return CoverageSummary(
        expected_intervals=coverage.expected_intervals,
        forecast_available=coverage.forecast_available,
        missing_forecast=coverage.missing_forecast,
        valid_pairs=coverage.valid_pairs,
        missing_actual=coverage.missing_actual,
        missing_both=coverage.missing_both,
        coverage_percent=coverage.coverage_percent,
        valid_pair_percent=coverage.valid_pair_percent,
        status_counts=coverage.status_counts,
    )


def freshness(service: AnalysisService, bundle: AnalysisBundle) -> DataFreshness:
    return DataFreshness(**service.data_freshness(bundle))


def _interval_fields(selection: ForecastSelection, tz: ZoneInfo) -> dict[str, object]:
    selected = selection.selected
    return {
        "delivery_start_utc": selection.delivery_start,
        "delivery_start_local": to_local_iso(selection.delivery_start, tz),
        "delivery_date_local": selection.delivery_start.astimezone(tz).date(),
        "cutoff_utc": selection.cutoff,
        "cutoff_local": to_local_iso(selection.cutoff, tz),
        "status": "available" if selected else "missing_forecast",
        "forecast_mw": selected.generation_mw if selected else None,
        "forecast_publication_utc": selected.publish_time if selected else None,
        "forecast_publication_local": to_local_iso(selected.publish_time, tz) if selected else None,
        "lead_time_hours": (
            _round((selection.delivery_start - selected.publish_time).total_seconds() / 3600, 2)
            if selected
            else None
        ),
        "eligible_forecast_count": selection.eligible_count,
        "duplicate_publication": selection.duplicate_publication,
        "stale_forecast": selection.stale,
        "previous_publication_utc": selection.previous.publish_time if selection.previous else None,
        "previous_forecast_mw": selection.previous.generation_mw if selection.previous else None,
    }


def forecast_interval(selection: ForecastSelection, tz: ZoneInfo) -> ForecastInterval:
    return ForecastInterval(**_interval_fields(selection, tz))


def comparison_interval(row: ComparisonRow, tz: ZoneInfo) -> ComparisonInterval:
    fields = _interval_fields(row.selection, tz)
    fields.update(
        {
            "status": row.status,
            "actual_mw": _round(row.actual_mw),
            "actual_half_hours": len(row.actual.half_hour_values),
            "signed_error_mw": _round(row.signed_error_mw),
            "absolute_error_mw": _round(row.absolute_error_mw),
            "squared_error_mw2": _round(row.squared_error_mw2),
            "absolute_percentage_error": _round(row.absolute_percentage_error, 2),
        }
    )
    return ComparisonInterval(**fields)


def forecast_summary(bundle: AnalysisBundle, tz: ZoneInfo) -> ForecastSummary:
    summary = bundle.forecast_summary
    expected = len(bundle.hours)
    available = int(summary["available"])
    pub_min = summary["publication_min"]
    pub_max = summary["publication_max"]
    return ForecastSummary(
        expected_intervals=expected,
        available=available,
        missing=expected - available,
        coverage_percent=round(available / expected * 100.0, 4) if expected else 0.0,
        distinct_publications=int(summary["distinct_publications"]),
        publication_min_utc=pub_min if isinstance(pub_min, object) else None,
        publication_min_local=to_local_iso(pub_min, tz) if pub_min else None,  # type: ignore[arg-type]
        publication_max_utc=pub_max if isinstance(pub_max, object) else None,
        publication_max_local=to_local_iso(pub_max, tz) if pub_max else None,  # type: ignore[arg-type]
        lead_time_min_hours=_round(summary["lead_time_min_hours"]),  # type: ignore[arg-type]
        lead_time_max_hours=_round(summary["lead_time_max_hours"]),  # type: ignore[arg-type]
        duplicate_publication_intervals=int(summary["duplicate_publication_intervals"]),
        stale_intervals=int(summary["stale_intervals"]),
    )


def build_forecast_response(service: AnalysisService, bundle: AnalysisBundle) -> ForecastResponse:
    tz = _zone(bundle)
    return ForecastResponse(
        query=query_summary(service, bundle),
        summary=forecast_summary(bundle, tz),
        intervals=[forecast_interval(bundle.selections[hour], tz) for hour in bundle.hours],
        data_source=freshness(service, bundle),
        warnings=bundle.warnings,
        data_quality=bundle.data_quality,
    )


def build_comparison_response(service: AnalysisService, bundle: AnalysisBundle) -> ComparisonResponse:
    tz = _zone(bundle)
    half_hours = [
        HalfHourActual(
            start_utc=record.start_time,
            start_local=to_local_iso(record.start_time, tz),
            generation_mw=record.generation_mw,
            settlement_date=record.settlement_date,
            settlement_period=record.settlement_period,
        )
        for record in bundle.half_hourly_actuals
    ]
    return ComparisonResponse(
        query=query_summary(service, bundle),
        coverage=coverage_summary(bundle.coverage),
        intervals=[comparison_interval(row, tz) for row in bundle.rows],
        half_hourly_actuals=half_hours,
        data_source=freshness(service, bundle),
        warnings=bundle.warnings,
        data_quality=bundle.data_quality,
    )


def accuracy_model(accuracy: AccuracyMetrics, tz: ZoneInfo) -> AccuracyMetricsModel:
    return AccuracyMetricsModel(
        mae_mw=accuracy.mae_mw,
        rmse_mw=accuracy.rmse_mw,
        mbe_mw=accuracy.mbe_mw,
        mape_percent=accuracy.mape_percent,
        mape_valid_count=accuracy.mape_valid_count,
        mape_excluded_count=accuracy.mape_excluded_count,
        max_abs_error_mw=accuracy.max_abs_error_mw,
        max_abs_error_at_utc=accuracy.max_abs_error_at,
        max_abs_error_at_local=to_local_iso(accuracy.max_abs_error_at, tz) if accuracy.max_abs_error_at else None,
    )


def histogram_model(histogram: ErrorHistogram) -> ErrorHistogramModel:
    return ErrorHistogramModel(
        bin_width_mw=histogram.bin_width_mw,
        total_pairs=histogram.total_pairs,
        bins=[
            HistogramBinModel(
                lower_mw=bin.lower_mw,
                upper_mw=bin.upper_mw,
                count=bin.count,
                signed_side=bin.signed_side,
            )
            for bin in histogram.bins
        ],
    )


def build_metrics_response(service: AnalysisService, bundle: AnalysisBundle) -> MetricsResponse:
    tz = _zone(bundle)
    return MetricsResponse(
        query=query_summary(service, bundle),
        coverage=coverage_summary(bundle.coverage),
        metrics=accuracy_model(bundle.accuracy, tz),
        decision_context=DecisionContext(**service.decision_context(bundle)),
        histogram=histogram_model(bundle.histogram),
        data_source=freshness(service, bundle),
        warnings=bundle.warnings,
        data_quality=bundle.data_quality,
    )


def daily_model(daily: DailyMetrics) -> DailyMetricModel:
    return DailyMetricModel(
        date=daily.day,
        expected_intervals=daily.expected_intervals,
        forecast_available=daily.forecast_available,
        valid_pairs=daily.valid_pairs,
        missing_forecast=daily.missing_forecast,
        missing_actual=daily.missing_actual,
        missing_both=daily.missing_both,
        coverage_percent=daily.coverage_percent,
        valid_pair_percent=daily.valid_pair_percent,
        mae_mw=daily.mae_mw,
        rmse_mw=daily.rmse_mw,
        mbe_mw=daily.mbe_mw,
        mape_percent=daily.mape_percent,
        mape_valid_count=daily.mape_valid_count,
        mape_excluded_count=daily.mape_excluded_count,
        max_abs_error_mw=daily.max_abs_error_mw,
    )


def build_daily_response(service: AnalysisService, bundle: AnalysisBundle) -> DailyMetricsResponse:
    return DailyMetricsResponse(
        query=query_summary(service, bundle),
        coverage=coverage_summary(bundle.coverage),
        daily=[daily_model(row) for row in bundle.daily],
        warnings=bundle.warnings,
    )
