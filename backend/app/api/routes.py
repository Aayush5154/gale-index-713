"""HTTP routes for the analysis API."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.presenters import (
    build_comparison_response,
    build_daily_response,
    build_forecast_response,
    build_metrics_response,
)
from app.core.config import Settings
from app.schemas.common import (
    DependencyStatus,
    HealthResponse,
    MetadataResponse,
)
from app.schemas.responses import (
    ComparisonResponse,
    DailyMetricsResponse,
    ForecastResponse,
    MetricsResponse,
)
from app.services.analysis import AnalysisQuery, AnalysisService, resolve_query
from app.services.metadata import build_metadata

UTC = timezone.utc
router = APIRouter(prefix="/api")


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


ServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_query(
    request: Request,
    from_date: Annotated[
        date | None,
        Query(description="First delivery date in Europe/London (YYYY-MM-DD). Defaults to 2026-01-01."),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(description="Last delivery date in Europe/London (YYYY-MM-DD). Defaults to 2026-01-31."),
    ] = None,
    cutoff_mode: Annotated[
        Literal["daily", "fixed"],
        Query(description="'daily' uses D-1 at cutoff_time for each delivery day; 'fixed' applies one timestamp."),
    ] = "daily",
    cutoff_time: Annotated[
        str | None,
        Query(description="London local cut-off time for daily mode, HH:MM. Defaults to 09:20."),
    ] = None,
    cutoff_datetime: Annotated[
        str | None,
        Query(
            description=(
                "ISO-8601 cut-off for fixed mode. A value without an offset is interpreted as Europe/London."
            )
        ),
    ] = None,
) -> AnalysisQuery:
    settings: Settings = request.app.state.settings
    return resolve_query(
        settings,
        from_date=from_date.isoformat() if from_date else None,
        to_date=to_date.isoformat() if to_date else None,
        cutoff_mode=cutoff_mode,
        cutoff_time=cutoff_time,
        cutoff_datetime=cutoff_datetime,
    )


QueryDep = Annotated[AnalysisQuery, Depends(get_query)]


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Application and dependency health",
)
async def health(request: Request, service: ServiceDep, settings: SettingsDep) -> HealthResponse:
    dependency = service.source.dependency_status()
    source_info = service.source.source_info()
    overall = "ok" if dependency.get("status") in {"ok", "fixture", "not_yet_called"} else "degraded"
    return HealthResponse(
        status=overall,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        data_mode=source_info["mode"],
        is_synthetic=bool(source_info["is_synthetic"]),
        timezone=settings.market_timezone,
        timestamp_utc=datetime.now(UTC),
        dependencies=[DependencyStatus(**dependency)],
        cache=service.source.cache_stats.as_dict(),
    )


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    tags=["System"],
    summary="Datasets, methodology, defaults and metric definitions",
)
async def metadata(service: ServiceDep, settings: SettingsDep) -> MetadataResponse:
    return build_metadata(settings, service.source)


@router.get(
    "/forecasts",
    response_model=ForecastResponse,
    tags=["Analysis"],
    summary="Decision-time forecast versions for each delivery hour",
)
async def forecasts(service: ServiceDep, query: QueryDep) -> ForecastResponse:
    bundle = await service.run(query)
    return build_forecast_response(service, bundle)


@router.get(
    "/comparison",
    response_model=ComparisonResponse,
    tags=["Analysis"],
    summary="Matched forecast/actual intervals with per-interval errors",
)
async def comparison(service: ServiceDep, query: QueryDep) -> ComparisonResponse:
    bundle = await service.run(query)
    return build_comparison_response(service, bundle)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Analysis"],
    summary="Aggregate accuracy metrics, coverage and error distribution",
)
async def metrics(service: ServiceDep, query: QueryDep) -> MetricsResponse:
    bundle = await service.run(query)
    return build_metrics_response(service, bundle)


@router.get(
    "/accuracy/daily",
    response_model=DailyMetricsResponse,
    tags=["Analysis"],
    summary="Daily accuracy summaries for the selected period",
)
async def daily(service: ServiceDep, query: QueryDep) -> DailyMetricsResponse:
    bundle = await service.run(query)
    return build_daily_response(service, bundle)
