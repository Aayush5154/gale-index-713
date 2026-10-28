"""End-to-end analysis orchestration.

One call reconstructs a decision-time forecast for every delivery hour in the
requested period, matches it to FUELHH outturn, and derives metrics.  Route
handlers only translate this result into their specific response models.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.errors import InvalidQueryError
from app.models.domain import ActualRecord, ForecastSelection, HourlyActual, NormalizationStats
from app.services.actuals import aggregate_hourly_actuals, half_hourly_window
from app.services.comparison import ComparisonRow, build_comparison
from app.services.elexon_client import WindDataSource
from app.services.forecast_selection import (
    select_decision_time_forecasts,
    summarise_publication_usage,
)
from app.services.metrics import (
    AccuracyMetrics,
    CoverageStats,
    DailyMetrics,
    ErrorHistogram,
    build_warnings,
    compute_accuracy,
    compute_coverage,
    compute_daily,
    compute_error_histogram,
)
from app.services.normalization import normalize_actual_records, normalize_forecast_records
from app.services.timeutils import (
    cutoff_for_delivery_day,
    cutoff_from_input,
    hourly_starts,
    local_day_bounds,
    parse_cutoff_time,
    to_local_iso,
)

logger = logging.getLogger(__name__)
UTC = timezone.utc
CutoffMode = Literal["daily", "fixed"]


@dataclass(frozen=True)
class AnalysisQuery:
    from_date: date
    to_date: date
    cutoff_mode: CutoffMode
    cutoff_time: time
    cutoff_datetime_utc: datetime | None
    timezone_name: str

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


@dataclass
class AnalysisBundle:
    query: AnalysisQuery
    delivery_start: datetime
    delivery_end: datetime
    hours: list[datetime]
    cutoffs: dict[datetime, datetime]
    selections: dict[datetime, ForecastSelection]
    hourly_actuals: dict[datetime, HourlyActual]
    half_hourly_actuals: list[ActualRecord]
    rows: list[ComparisonRow]
    coverage: CoverageStats
    accuracy: AccuracyMetrics
    daily: list[DailyMetrics]
    histogram: ErrorHistogram
    forecast_summary: dict[str, object]
    data_quality: dict[str, object]
    warnings: list[str]
    generated_at: datetime
    fetch_counts: dict[str, int]


def resolve_query(
    settings: Settings,
    *,
    from_date: str | None,
    to_date: str | None,
    cutoff_mode: str,
    cutoff_time: str | None,
    cutoff_datetime: str | None,
) -> AnalysisQuery:
    tz = ZoneInfo(settings.market_timezone)

    try:
        start = date.fromisoformat(from_date) if from_date else date.fromisoformat(settings.default_from_date)
        end = date.fromisoformat(to_date) if to_date else date.fromisoformat(settings.default_to_date)
    except ValueError as exc:
        raise InvalidQueryError(
            "Dates must use the YYYY-MM-DD format.",
            details={"field": "from_date/to_date"},
        ) from exc

    if end < start:
        raise InvalidQueryError("The end date must be on or after the start date.", details={"field": "to_date"})
    range_days = (end - start).days + 1
    if range_days > settings.max_range_days:
        raise InvalidQueryError(
            f"The requested period is {range_days} days. The maximum is {settings.max_range_days} days.",
            details={"field": "to_date", "max_range_days": settings.max_range_days},
        )
    if end > datetime.now(tz).date():
        raise InvalidQueryError(
            "The delivery period cannot extend beyond today in Europe/London.",
            details={"field": "to_date"},
        )

    if cutoff_mode not in ("daily", "fixed"):
        raise InvalidQueryError(
            "Cutoff mode must be 'daily' or 'fixed'.", details={"field": "cutoff_mode"}
        )

    try:
        cutoff_clock = parse_cutoff_time(cutoff_time or settings.default_cutoff_time)
    except InvalidQueryError:
        raise

    cutoff_utc: datetime | None = None
    if cutoff_mode == "fixed":
        if not cutoff_datetime:
            raise InvalidQueryError(
                "A fixed decision cut-off requires cutoff_datetime.",
                details={"field": "cutoff_datetime"},
            )
        try:
            text = cutoff_datetime.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise InvalidQueryError(
                "cutoff_datetime must be an ISO-8601 timestamp.",
                details={"field": "cutoff_datetime"},
            ) from exc

        # A naive value is interpreted as London local time, which makes the
        # UI's datetime-local input unambiguous.
        cutoff_utc = cutoff_from_input(parsed, tz)
        delivery_start, _ = local_day_bounds(start, end, tz)
        if cutoff_utc >= delivery_start:
            raise InvalidQueryError(
                "A fixed decision cut-off must be before the first delivery interval.",
                details={"field": "cutoff_datetime"},
            )

    return AnalysisQuery(
        from_date=start,
        to_date=end,
        cutoff_mode=cutoff_mode,  # type: ignore[arg-type]
        cutoff_time=cutoff_clock,
        cutoff_datetime_utc=cutoff_utc,
        timezone_name=settings.market_timezone,
    )


class AnalysisService:
    def __init__(self, settings: Settings, source: WindDataSource) -> None:
        self._settings = settings
        self._source = source
        self._tz = ZoneInfo(settings.market_timezone)

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def source(self) -> WindDataSource:
        return self._source

    def _cutoffs(self, query: AnalysisQuery, hours: list[datetime]) -> dict[datetime, datetime]:
        if query.cutoff_mode == "fixed":
            assert query.cutoff_datetime_utc is not None
            return {hour: query.cutoff_datetime_utc for hour in hours}
        return {
            hour: cutoff_for_delivery_day(hour.astimezone(self._tz).date(), query.cutoff_time, self._tz)
            for hour in hours
        }

    async def run(self, query: AnalysisQuery) -> AnalysisBundle:
        delivery_start, delivery_end = local_day_bounds(query.from_date, query.to_date, self._tz)
        hours = hourly_starts(delivery_start, delivery_end)
        if not hours:
            raise InvalidQueryError("The requested delivery period contains no hourly intervals.")
        cutoffs = self._cutoffs(query, hours)

        first_cutoff = min(cutoffs.values())
        last_cutoff = max(cutoffs.values())
        if query.cutoff_mode == "fixed":
            publish_from = first_cutoff - timedelta(days=self._settings.elexon_forecast_lookback_days)
            publish_to = first_cutoff
        else:
            publish_from = first_cutoff - timedelta(days=self._settings.elexon_forecast_lookback_days)
            publish_to = last_cutoff

        actual_task = self._source.fetch_actuals(query.from_date, query.to_date)
        forecast_task = self._source.fetch_forecasts(publish_from, publish_to)
        actual_fetch, forecast_fetch = await asyncio.gather(actual_task, forecast_task)

        forecasts, forecast_stats = normalize_forecast_records(forecast_fetch.records)
        actuals, actual_stats = normalize_actual_records(actual_fetch.records)

        half_hourly = half_hourly_window(actuals, delivery_start, delivery_end)
        hourly_actuals = aggregate_hourly_actuals(half_hourly, hours)
        hour_set = set(hours)
        forecast_versions_in_period = sum(1 for record in forecasts if record.start_time in hour_set)

        selections = select_decision_time_forecasts(
            hours=hours,
            cutoffs=cutoffs,
            records=forecasts,
            stale_after_hours=self._settings.stale_forecast_hours,
        )
        rows = build_comparison(
            hours=hours,
            cutoffs=cutoffs,
            selections=selections,
            hourly_actuals=hourly_actuals,
            mape_min_actual_mw=self._settings.mape_min_actual_mw,
        )
        coverage = compute_coverage(rows)
        accuracy = compute_accuracy(rows)
        daily = compute_daily(rows, self._tz)
        histogram = compute_error_histogram(rows)
        forecast_summary = summarise_publication_usage(selections)
        incomplete_hours = sum(1 for actual in hourly_actuals.values() if not actual.complete)

        data_quality: dict[str, object] = {
            "actual": actual_stats.as_dict(),
            "forecast": forecast_stats.as_dict(),
            "actual_records_in_window": len(half_hourly),
            "forecast_versions_in_period": forecast_versions_in_period,
            "incomplete_actual_hours": incomplete_hours,
            "expected_half_hours": len(hours) * 2,
            "actual_half_hours_used": len(half_hourly),
        }
        warnings = build_warnings(
            rows=rows,
            coverage=coverage,
            accuracy=accuracy,
            actual_stats=actual_stats,
            forecast_stats=forecast_stats,
            incomplete_hours=incomplete_hours,
        )
        warnings.extend(forecast_stats.warnings)
        warnings.extend(actual_stats.warnings)
        if not forecast_fetch.records:
            warnings.append("The Elexon WINDFOR query returned no forecast records for the derived publication window.")
        if not actual_fetch.records:
            warnings.append("The Elexon FUELHH query returned no WIND outturn records for the requested period.")

        return AnalysisBundle(
            query=query,
            delivery_start=delivery_start,
            delivery_end=delivery_end,
            hours=hours,
            cutoffs=cutoffs,
            selections=selections,
            hourly_actuals=hourly_actuals,
            half_hourly_actuals=half_hourly,
            rows=rows,
            coverage=coverage,
            accuracy=accuracy,
            daily=daily,
            histogram=histogram,
            forecast_summary=forecast_summary,
            data_quality=data_quality,
            warnings=warnings,
            generated_at=datetime.now(UTC),
            fetch_counts={
                "actual_records": len(actual_fetch.records),
                "forecast_records": len(forecast_fetch.records),
                "actual_chunks": actual_fetch.chunks_requested,
                "forecast_chunks": forecast_fetch.chunks_requested,
            },
        )

    def decision_context(self, bundle: AnalysisBundle) -> dict[str, object]:
        first = min(bundle.cutoffs.values())
        last = max(bundle.cutoffs.values())
        summary = bundle.forecast_summary
        if bundle.query.cutoff_mode == "daily":
            rule = (
                f"For each delivery day, the latest forecast published at or before "
                f"{bundle.query.cutoff_time.strftime('%H:%M')} Europe/London on the previous day."
            )
        else:
            assert bundle.query.cutoff_datetime_utc is not None
            rule = "One fixed cut-off timestamp applies to every delivery interval in the period."
        return {
            "mode": bundle.query.cutoff_mode,
            "timezone": bundle.query.timezone_name,
            "cutoff_time_local": bundle.query.cutoff_time.strftime("%H:%M"),
            "first_cutoff_utc": first,
            "first_cutoff_local": to_local_iso(first, self._tz),
            "last_cutoff_utc": last,
            "last_cutoff_local": to_local_iso(last, self._tz),
            "fixed_cutoff_utc": bundle.query.cutoff_datetime_utc,
            "fixed_cutoff_local": (
                to_local_iso(bundle.query.cutoff_datetime_utc, self._tz)
                if bundle.query.cutoff_datetime_utc
                else None
            ),
            "rule": rule,
            "distinct_publications": summary["distinct_publications"],
            "earliest_publication_utc": summary["publication_min"],
            "latest_publication_utc": summary["publication_max"],
            "lead_time_min_hours": summary["lead_time_min_hours"],
            "lead_time_max_hours": summary["lead_time_max_hours"],
        }

    def query_summary(self, bundle: AnalysisBundle) -> dict[str, object]:
        return {
            "from_date": bundle.query.from_date.isoformat(),
            "to_date": bundle.query.to_date.isoformat(),
            "timezone": bundle.query.timezone_name,
            "cutoff_mode": bundle.query.cutoff_mode,
            "cutoff_time_local": bundle.query.cutoff_time.strftime("%H:%M"),
            "cutoff_datetime_utc": bundle.query.cutoff_datetime_utc,
            "cutoff_datetime_local": (
                to_local_iso(bundle.query.cutoff_datetime_utc, self._tz)
                if bundle.query.cutoff_datetime_utc
                else None
            ),
            "delivery_start_utc": bundle.delivery_start,
            "delivery_end_utc": bundle.delivery_end,
            "delivery_start_local": to_local_iso(bundle.delivery_start, self._tz),
            "delivery_end_local": to_local_iso(bundle.delivery_end, self._tz),
            "expected_intervals": len(bundle.hours),
            "resolution": "hourly",
        }

    def data_freshness(self, bundle: AnalysisBundle) -> dict[str, object]:
        stats = self._source.cache_stats
        info = self._source.source_info()
        return {
            "data_mode": info["mode"],
            "is_synthetic": bool(info["is_synthetic"]),
            "source_name": info["name"],
            "generated_at_utc": bundle.generated_at,
            "cache_ttl_seconds": self._settings.cache_ttl_seconds,
            "cache": stats.as_dict(),
            "fetch": bundle.fetch_counts,
        }

    async def prewarm_default(self) -> None:
        try:
            query = resolve_query(
                self._settings,
                from_date=self._settings.default_from_date,
                to_date=self._settings.default_to_date,
                cutoff_mode="daily",
                cutoff_time=self._settings.default_cutoff_time,
                cutoff_datetime=None,
            )
            await self.run(query)
            logger.info("Default January 2026 range pre-warmed into the raw data cache.")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - depends on external availability
            logger.warning("Pre-warm of the default range failed: %s", type(exc).__name__)


def normalisation_summary(stats: NormalizationStats) -> dict[str, int]:
    return stats.as_dict()
