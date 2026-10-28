"""Static metadata and methodology content exposed by the API."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.config import Settings
from app.schemas.common import (
    CutoffInfo,
    DataQualityRule,
    DatasetField,
    DatasetInfo,
    MetadataResponse,
    MetricDefinition,
    Period,
    ResolutionInfo,
    UnitsInfo,
)
from app.services.elexon_client import WindDataSource

UTC = timezone.utc


def build_metadata(settings: Settings, source: WindDataSource) -> MetadataResponse:
    source_info = source.source_info()
    target = Period(
        from_date=date.fromisoformat(settings.default_from_date),
        to_date=date.fromisoformat(settings.default_to_date),
    )
    supported = target if source_info["mode"] == "fixture" else None
    supported_note = (
        "Fixture mode contains synthetic data for the target period only."
        if source_info["mode"] == "fixture"
        else (
            "Data is queried from the public Elexon Insights API on demand. Availability depends on "
            "the upstream datasets; each request is capped at "
            f"{settings.max_range_days} days. This deployment targets January 2026."
        )
    )

    datasets = [
        DatasetInfo(
            key="FUELHH",
            name="Half-hourly generation outturn by fuel type",
            description=(
                "Elexon outturn generation by fuel category. Records are filtered to fuelType=WIND. "
                "Values are average MW over each 30-minute settlement period."
            ),
            endpoint=f"{settings.elexon_base_url}/datasets/FUELHH/stream",
            documentation_url="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream",
            resolution="Half-hourly (30-minute average MW)",
            fields=[
                DatasetField(name="publishTime", description="Publication timestamp (UTC)."),
                DatasetField(name="startTime", description="Start of the 30-minute delivery interval (UTC)."),
                DatasetField(name="settlementDate", description="GB settlement date (Europe/London calendar day)."),
                DatasetField(name="settlementPeriod", description="Settlement period 1-48 (1-50 on a clock-change day)."),
                DatasetField(name="fuelType", description="Fuel category; only WIND is retained."),
                DatasetField(name="generation", description="Average generation over the interval, in MW."),
            ],
        ),
        DatasetInfo(
            key="WINDFOR",
            name="Wind generation forecast",
            description=(
                "NESO wind generation forecast published through Elexon. The dataset is hourly and is "
                "updated by NESO up to eight times a day. Retrieval is filtered by publication time."
            ),
            endpoint=f"{settings.elexon_base_url}/datasets/WINDFOR/stream",
            documentation_url="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream",
            resolution="Hourly (one MW value per delivery hour)",
            fields=[
                DatasetField(name="publishTime", description="Timestamp at which this forecast version was published (UTC)."),
                DatasetField(name="startTime", description="Start of the delivery hour (UTC)."),
                DatasetField(name="generation", description="Forecast wind generation, in MW."),
            ],
        ),
    ]

    metric_definitions = [
        MetricDefinition(
            key="mae",
            label="Mean Absolute Error (MAE)",
            formula="mean(|forecast - actual|)",
            unit="MW",
            interpretation="The average absolute forecast error in MW. Lower is better.",
        ),
        MetricDefinition(
            key="rmse",
            label="Root Mean Squared Error (RMSE)",
            formula="sqrt(mean((forecast - actual)^2))",
            unit="MW",
            interpretation="Like MAE but gives more weight to large errors. Lower is better.",
        ),
        MetricDefinition(
            key="mbe",
            label="Mean Bias Error (MBE)",
            formula="mean(forecast - actual)",
            unit="MW",
            interpretation=(
                "Signed average error. Positive values indicate forecasts tended to overpredict wind "
                "generation; negative values indicate underpredictions."
            ),
        ),
        MetricDefinition(
            key="mape",
            label="Mean Absolute Percentage Error (MAPE)",
            formula="mean(|forecast - actual| / actual) x 100, for actual >= threshold",
            unit="%",
            interpretation=(
                "Relative error, calculated only where the actual value is at least the configured "
                f"denominator threshold ({settings.mape_min_actual_mw:g} MW). It is unstable near zero and "
                "is not a substitute for MW-based metrics."
            ),
        ),
        MetricDefinition(
            key="coverage",
            label="Forecast coverage",
            formula="intervals with an eligible forecast / expected intervals x 100",
            unit="%",
            interpretation=(
                "Availability of an eligible forecast version at the cut-off. Coverage is not accuracy."
            ),
        ),
    ]

    quality_rules = [
        DataQualityRule(
            topic="Fuel filtering",
            handling="FUELHH records are retained only when fuelType equals WIND (case-insensitive).",
        ),
        DataQualityRule(
            topic="Timestamp normalisation",
            handling=(
                "All source timestamps are parsed to timezone-aware UTC. UK market dates and cut-offs are "
                "displayed in Europe/London; daylight-saving transitions are handled by the IANA database."
            ),
        ),
        DataQualityRule(
            topic="Forecast eligibility",
            handling=(
                "A WINDFOR record is eligible only when startTime equals the delivery hour and publishTime "
                "is <= the decision cut-off and strictly before the delivery hour. The latest eligible "
                "publication wins; a future publication is never used."
            ),
        ),
        DataQualityRule(
            topic="Duplicate forecasts",
            handling=(
                "Exact duplicates are collapsed. If several eligible records share the winning publication "
                "time, the highest generation value is selected as a deterministic tie-break and the interval "
                "is flagged."
            ),
        ),
        DataQualityRule(
            topic="Duplicate actuals",
            handling=(
                "For repeated FUELHH records at the same delivery interval, the latest publication wins; "
                "conflicting values at the same publication time are resolved to the higher value and counted."
            ),
        ),
        DataQualityRule(
            topic="Missing forecasts",
            handling=(
                "No eligible forecast marks the interval unavailable. No future or older ineligible forecast "
                "is substituted. Missing intervals are excluded from error metrics and counted in coverage."
            ),
        ),
        DataQualityRule(
            topic="Hourly comparison",
            handling=(
                "WINDFOR is hourly and FUELHH is half-hourly. A comparison hour uses the arithmetic mean of "
                "its two half-hourly average-MW readings at :00 and :30. No half-hourly forecast is invented."
            ),
        ),
        DataQualityRule(
            topic="Zero or near-zero actuals",
            handling=(
                "MAPE is not calculated when actual generation is below the configured denominator threshold "
                f"({settings.mape_min_actual_mw:g} MW). MAE, RMSE and MBE still use the pair. Exclusions are reported."
            ),
        ),
        DataQualityRule(
            topic="Invalid values",
            handling=(
                "Missing, non-numeric, non-finite or negative generation values are skipped and counted. "
                "An interval with fewer than two valid half-hourly readings is treated as a missing actual."
            ),
        ),
        DataQualityRule(
            topic="Units",
            handling=(
                "Generation is average power in MW over the stated interval. No MW-to-MWh conversion is applied "
                "and no energy volume is reported."
            ),
        ),
    ]

    limitations = [
        "WINDFOR publishes hourly forecasts. The tool cannot produce a half-hourly forecast series, and it "
        "does not fabricate one.",
        "The two datasets are not identical measurement populations: WINDFOR covers wind farms visible to "
        "NESO with operational metering, while FUELHH WIND is aggregated transmission-connected outturn and "
        "excludes embedded wind. A persistent bias can therefore reflect coverage or basis differences as "
        "well as forecast error. No adjustment is applied.",
        "The default 09:20 Europe/London cut-off represents the EPEX GB 60-minute day-ahead auction gate "
        "closure on D-1. It is configurable because market gate closures and internal procurement deadlines "
        "vary. It is not asserted to be the client's only decision time.",
        "Only national wind generation is analysed. Demand, prices, generation mix and procurement volumes "
        "are outside scope, so the tool does not calculate financial savings or recommend a procurement quantity.",
        "Elexon records can be revised. Actual outturn uses the latest available publication for each interval; "
        "historical analyses can therefore differ slightly from a report produced earlier.",
        "MAPE is unreliable when actual wind generation is near zero. The configured threshold and excluded "
        "count are disclosed rather than silently applying the metric.",
        "Upstream API availability, latency and rate limits affect freshness. Cached raw chunks may be up to "
        f"{settings.cache_ttl_seconds // 60} minutes old.",
    ]

    return MetadataResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        data_mode=source_info["mode"],
        is_synthetic=bool(source_info["is_synthetic"]),
        timezone=settings.market_timezone,
        generated_at_utc=datetime.now(UTC),
        target_period=target,
        supported_range=supported,
        supported_range_note=supported_note,
        max_range_days=settings.max_range_days,
        cutoff=CutoffInfo(
            default_mode="daily",
            default_time_local=settings.default_cutoff_time,
            timezone=settings.market_timezone,
            rule=(
                "For each delivery day D, use the latest forecast published at or before "
                f"{settings.default_cutoff_time} Europe/London on D-1."
            ),
            reference=(
                "EPEX SPOT GB 60-minute day-ahead auction gate closure (09:20 GMT/BST on D-1). "
                "The 30-minute GB day-ahead auction closes later, at 15:30 GMT/BST."
            ),
            reference_url="https://www.epexspot.com/en/tradingproducts",
            alternatives=[
                "Daily D-1 cut-off at a configurable London time (default 09:20).",
                "One fixed timestamp applied to every interval, for a specific historical decision.",
                "N2EX's separate GB day-ahead auction closes at 09:50 London on D-1.",
            ],
        ),
        resolution=ResolutionInfo(
            forecast="hourly",
            actual="half-hourly",
            comparison="hourly",
            explanation=(
                "Each hourly WINDFOR value is matched to the same delivery hour. The hourly actual is the "
                "arithmetic mean of the two FUELHH half-hourly average-MW values. The original half-hourly "
                "outturn is shown in the explorer chart for context."
            ),
        ),
        units=UnitsInfo(
            generation="MW (average power over the delivery interval)",
            energy="Not reported; no MWh conversion is applied",
            note=(
                "MW values are average power. A 30-minute interval could be converted to MWh by multiplying "
                "average MW by 0.5 hours, but this analysis deliberately does not do so."
            ),
        ),
        datasets=datasets,
        metric_definitions=metric_definitions,
        data_quality_rules=quality_rules,
        limitations=limitations,
    )
