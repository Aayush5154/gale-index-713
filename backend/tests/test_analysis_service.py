from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.analysis import AnalysisService, resolve_query
from app.services.elexon_client import FixtureClient
from tests.fakes import StaticSource, two_day_records


def make_settings(**overrides) -> Settings:
    values = {
        "prewarm_default_range": False,
        "default_from_date": "2026-01-01",
        "default_to_date": "2026-01-02",
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(**values)


def daily_query(settings: Settings, start="2026-01-01", end="2026-01-02"):
    return resolve_query(
        settings,
        from_date=start,
        to_date=end,
        cutoff_mode="daily",
        cutoff_time="09:20",
        cutoff_datetime=None,
    )


@pytest.mark.asyncio
async def test_analysis_selects_latest_eligible_version_per_delivery_day():
    actuals, forecasts = two_day_records()
    service = AnalysisService(make_settings(), StaticSource(actuals, forecasts))
    bundle = await service.run(daily_query(service.settings))

    assert len(bundle.hours) == 48
    assert bundle.coverage.expected_intervals == 48
    assert bundle.coverage.valid_pairs == 48
    assert bundle.coverage.coverage_percent == 100.0
    assert bundle.accuracy.mae_mw == pytest.approx(750.0)
    assert bundle.accuracy.mbe_mw == pytest.approx(750.0)
    assert bundle.accuracy.rmse_mw == pytest.approx((625000) ** 0.5)

    jan_1 = bundle.selections[bundle.hours[0]]
    jan_2 = bundle.selections[bundle.hours[24]]
    assert jan_1.selected is not None and jan_1.selected.generation_mw == 10500
    assert jan_1.selected.publish_time.isoformat() == "2025-12-31T07:30:00+00:00"
    assert jan_2.selected is not None and jan_2.selected.generation_mw == 11000
    assert jan_2.selected.publish_time.isoformat() == "2026-01-01T07:30:00+00:00"

    # The 11:30 post-cutoff distractor never leaks into the analysis.
    assert all(row.forecast_mw != 99999 for row in bundle.rows)
    assert bundle.forecast_summary["distinct_publications"] == 2


@pytest.mark.asyncio
async def test_analysis_marks_missing_forecast_and_excludes_from_metrics():
    actuals, forecasts = two_day_records()
    forecasts = [
        record
        for record in forecasts
        if not (
            record["publishTime"] == "2025-12-31T07:30:00Z"
            and record["startTime"] == "2026-01-01T05:00:00Z"
        )
    ]
    service = AnalysisService(make_settings(), StaticSource(actuals, forecasts))
    bundle = await service.run(daily_query(service.settings))

    assert bundle.coverage.missing_forecast == 1
    assert bundle.coverage.valid_pairs == 47
    missing = [row for row in bundle.rows if row.status == "missing_forecast"]
    assert len(missing) == 1
    assert missing[0].delivery_start.isoformat() == "2026-01-01T05:00:00+00:00"
    assert any("no eligible forecast" in warning for warning in bundle.warnings)
    assert bundle.accuracy.mae_mw is not None


@pytest.mark.asyncio
async def test_fixed_cutoff_applies_to_all_intervals():
    actuals, forecasts = two_day_records()
    settings = make_settings()
    service = AnalysisService(settings, StaticSource(actuals, forecasts))
    query = resolve_query(
        settings,
        from_date="2026-01-02",
        to_date="2026-01-02",
        cutoff_mode="fixed",
        cutoff_time="09:20",
        cutoff_datetime="2026-01-01T09:20",
    )
    bundle = await service.run(query)
    assert all(cutoff.isoformat() == "2026-01-01T09:20:00+00:00" for cutoff in bundle.cutoffs.values())
    assert bundle.rows[0].forecast_mw == 11000
    assert bundle.rows[0].selection.selected.publish_time.isoformat() == "2026-01-01T07:30:00+00:00"


@pytest.mark.asyncio
async def test_fixture_dataset_full_january_exercises_edge_cases():
    settings = make_settings(
        data_mode="fixture",
        default_from_date="2026-01-01",
        default_to_date="2026-01-31",
    )
    service = AnalysisService(settings, FixtureClient(settings))
    bundle = await service.run(daily_query(service.settings, "2026-01-01", "2026-01-31"))

    assert len(bundle.hours) == 744
    assert bundle.coverage.expected_intervals == 744
    assert bundle.coverage.missing_forecast >= 1
    assert bundle.coverage.missing_actual >= 1
    assert bundle.coverage.valid_pairs < 744
    assert bundle.accuracy.mae_mw is not None
    assert bundle.accuracy.mape_excluded_count >= 1

    missing_forecast = [row for row in bundle.rows if row.status == "missing_forecast"]
    assert any(row.delivery_start.isoformat() == "2026-01-10T05:00:00+00:00" for row in missing_forecast)

    missing_actual = [row for row in bundle.rows if row.status == "missing_actual"]
    assert any(row.delivery_start.isoformat() == "2026-01-12T03:00:00+00:00" for row in missing_actual)

    duplicate = [row for row in bundle.rows if row.selection.duplicate_publication]
    assert any(row.delivery_start.isoformat() == "2026-01-16T12:00:00+00:00" for row in duplicate)

    assert bundle.data_quality["actual"]["skipped_non_wind"] >= 1
    assert bundle.data_quality["actual"]["skipped_invalid_generation"] >= 1


def test_resolve_query_rejects_invalid_ranges():
    settings = make_settings()
    with pytest.raises(Exception):
        resolve_query(settings, from_date="2026-01-05", to_date="2026-01-01", cutoff_mode="daily", cutoff_time=None, cutoff_datetime=None)
    with pytest.raises(Exception):
        resolve_query(settings, from_date="2026-01-01", to_date="2027-01-01", cutoff_mode="daily", cutoff_time=None, cutoff_datetime=None)
    with pytest.raises(Exception):
        resolve_query(settings, from_date="2026-01-01", to_date="2026-01-02", cutoff_mode="fixed", cutoff_time=None, cutoff_datetime=None)
    with pytest.raises(Exception):
        resolve_query(
            settings,
            from_date="2026-01-02",
            to_date="2026-01-02",
            cutoff_mode="fixed",
            cutoff_time=None,
            cutoff_datetime="2026-01-02T00:00",
        )
