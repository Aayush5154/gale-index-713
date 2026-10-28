from __future__ import annotations

from datetime import timedelta

from app.services.forecast_selection import (
    index_forecasts_by_delivery,
    select_decision_time_forecasts,
    summarise_publication_usage,
)
from app.services.normalization import normalize_forecast_records
from tests.builders import utc, windfor_row

HOUR = utc(2026, 1, 10, 0, 0)
CUTOFF = utc(2026, 1, 9, 9, 20)


def select(rows, hour=HOUR, cutoff=CUTOFF, stale_after_hours=48.0):
    records, _ = normalize_forecast_records(rows)
    return select_decision_time_forecasts(
        hours=[hour],
        cutoffs={hour: cutoff},
        records=records,
        stale_after_hours=stale_after_hours,
    )[hour]


def test_latest_eligible_forecast_is_selected():
    rows = [
        windfor_row(HOUR, utc(2026, 1, 8, 22, 30), 1000),
        windfor_row(HOUR, utc(2026, 1, 9, 7, 30), 2000),
        windfor_row(HOUR, utc(2026, 1, 9, 11, 30), 3000),
    ]
    selection = select(rows)
    assert selection.selected is not None
    assert selection.selected.generation_mw == 2000
    assert selection.selected.publish_time == utc(2026, 1, 9, 7, 30)
    assert selection.eligible_count == 2
    assert selection.previous is not None
    assert selection.previous.generation_mw == 1000


def test_forecast_published_after_cutoff_is_rejected():
    rows = [
        windfor_row(HOUR, utc(2026, 1, 9, 7, 30), 2000),
        windfor_row(HOUR, utc(2026, 1, 9, 11, 30), 9999),
    ]
    selection = select(rows)
    assert selection.selected is not None
    assert selection.selected.generation_mw == 2000
    assert selection.eligible_count == 1


def test_forecast_published_at_cutoff_is_eligible():
    rows = [windfor_row(HOUR, CUTOFF, 2000)]
    selection = select(rows)
    assert selection.selected is not None
    assert selection.selected.generation_mw == 2000


def test_missing_forecast_is_marked_unavailable_without_substitution():
    rows = [windfor_row(HOUR, utc(2026, 1, 9, 11, 30), 5000)]
    selection = select(rows)
    assert selection.selected is None
    assert selection.available is False
    assert selection.eligible_count == 0


def test_forecast_for_another_delivery_hour_is_not_used():
    rows = [
        windfor_row(HOUR + timedelta(hours=1), utc(2026, 1, 9, 7, 30), 5000),
        windfor_row(HOUR - timedelta(hours=1), utc(2026, 1, 9, 7, 30), 4000),
    ]
    selection = select(rows)
    assert selection.selected is None


def test_forecast_published_at_or_after_delivery_is_never_eligible():
    later_cutoff = HOUR + timedelta(hours=2)
    rows = [
        windfor_row(HOUR, HOUR, 5000),
        windfor_row(HOUR, HOUR + timedelta(hours=1), 6000),
    ]
    selection = select(rows, cutoff=later_cutoff)
    assert selection.selected is None


def test_duplicate_publication_time_uses_deterministic_highest_value_and_flags():
    publish = utc(2026, 1, 9, 7, 30)
    rows = [
        windfor_row(HOUR, publish, 2000),
        windfor_row(HOUR, publish, 2400),
    ]
    selection = select(rows)
    assert selection.selected is not None
    assert selection.selected.generation_mw == 2400
    assert selection.duplicate_publication is True


def test_stale_forecast_is_flagged():
    rows = [windfor_row(HOUR, utc(2026, 1, 5, 7, 30), 2000)]
    selection = select(rows, stale_after_hours=48)
    assert selection.stale is True


def test_index_groups_versions_by_delivery_hour():
    rows = [
        windfor_row(HOUR, utc(2026, 1, 9, 7, 30), 2000),
        windfor_row(HOUR, utc(2026, 1, 9, 4, 30), 1900),
        windfor_row(HOUR + timedelta(hours=1), utc(2026, 1, 9, 7, 30), 2100),
    ]
    records, _ = normalize_forecast_records(rows)
    index = index_forecasts_by_delivery(records)
    assert len(index[HOUR]) == 2
    assert len(index[HOUR + timedelta(hours=1)]) == 1


def test_publication_usage_summary():
    rows = [
        windfor_row(HOUR, utc(2026, 1, 9, 7, 30), 2000),
        windfor_row(HOUR + timedelta(hours=1), utc(2026, 1, 9, 7, 30), 2100),
    ]
    records, _ = normalize_forecast_records(rows)
    selections = select_decision_time_forecasts(
        hours=[HOUR, HOUR + timedelta(hours=1)],
        cutoffs={HOUR: CUTOFF, HOUR + timedelta(hours=1): CUTOFF},
        records=records,
    )
    summary = summarise_publication_usage(selections)
    assert summary["available"] == 2
    assert summary["missing"] == 0
    assert summary["distinct_publications"] == 1
    assert summary["lead_time_min_hours"] == 16.5
    assert summary["lead_time_max_hours"] == 17.5
