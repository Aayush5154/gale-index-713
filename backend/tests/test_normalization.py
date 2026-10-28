from __future__ import annotations

import math
from datetime import timedelta

from app.services.normalization import (
    normalize_actual_records,
    normalize_forecast_records,
    parse_generation_mw,
)
from tests.builders import fuelhh_row, utc, windfor_row


def test_parse_generation_accepts_numeric_and_rejects_invalid_values():
    assert parse_generation_mw(1234) == 1234.0
    assert parse_generation_mw("1234.5") == 1234.5
    assert parse_generation_mw(0) == 0.0
    for value in (None, "", "abc", -1, -0.5, True, False, math.nan, math.inf):
        assert parse_generation_mw(value) is None


def test_actual_filter_keeps_only_wind():
    start = utc(2026, 1, 1, 0, 0)
    records = [
        fuelhh_row(start, 1000, fuel_type="WIND"),
        fuelhh_row(start + timedelta(minutes=30), 2000, fuel_type="NUCLEAR"),
        fuelhh_row(start + timedelta(hours=1), 3000, fuel_type="wind"),
    ]
    normalised, stats = normalize_actual_records(records)
    assert [record.generation_mw for record in normalised] == [1000.0, 3000.0]
    assert stats.skipped_non_wind == 1
    assert stats.valid == 2


def test_actual_timestamps_are_normalised_to_utc():
    row = fuelhh_row(utc(2026, 1, 1, 0, 0), 1000, publish=utc(2026, 1, 1, 1, 0))
    row["startTime"] = "2026-01-01T01:00:00+01:00"
    normalised, stats = normalize_actual_records([row])
    assert normalised[0].start_time == utc(2026, 1, 1, 0, 0)
    assert normalised[0].start_time.tzinfo is not None
    assert stats.valid == 1


def test_actual_revision_uses_latest_publication():
    start = utc(2026, 1, 1, 0, 0)
    records = [
        fuelhh_row(start, 1000, publish=utc(2026, 1, 1, 0, 30)),
        fuelhh_row(start, 1100, publish=utc(2026, 1, 1, 1, 0)),
    ]
    normalised, stats = normalize_actual_records(records)
    assert len(normalised) == 1
    assert normalised[0].generation_mw == 1100
    assert stats.duplicate_superseded == 1


def test_actual_conflicting_values_at_same_publication_are_flagged():
    start = utc(2026, 1, 1, 0, 0)
    publish = utc(2026, 1, 1, 1, 0)
    records = [
        fuelhh_row(start, 1000, publish=publish),
        fuelhh_row(start, 1200, publish=publish),
    ]
    normalised, stats = normalize_actual_records(records)
    assert normalised[0].generation_mw == 1200
    assert stats.ambiguous_duplicates == 1


def test_actual_exact_duplicates_are_collapsed():
    start = utc(2026, 1, 1, 0, 0)
    row = fuelhh_row(start, 1000)
    normalised, stats = normalize_actual_records([row, dict(row)])
    assert len(normalised) == 1
    assert stats.duplicate_exact == 1


def test_invalid_actual_generation_is_skipped():
    start = utc(2026, 1, 1, 0, 0)
    records = [
        fuelhh_row(start, None),
        fuelhh_row(start + timedelta(minutes=30), "not-a-number"),
        fuelhh_row(start + timedelta(hours=1), 1500),
    ]
    normalised, stats = normalize_actual_records(records)
    assert [record.generation_mw for record in normalised] == [1500.0]
    assert stats.skipped_invalid_generation == 2


def test_non_fuelhh_dataset_is_rejected():
    row = fuelhh_row(utc(2026, 1, 1, 0, 0), 1000, dataset="WINDFOR")
    normalised, stats = normalize_actual_records([row])
    assert normalised == []
    assert stats.skipped_wrong_dataset == 1


def test_forecast_versions_are_retained_and_sorted():
    start = utc(2026, 1, 1, 0, 0)
    records = [
        windfor_row(start, utc(2026, 1, 1, 7, 30), 1200),
        windfor_row(start, utc(2025, 12, 31, 7, 30), 1000),
    ]
    normalised, stats = normalize_forecast_records(records)
    assert [record.generation_mw for record in normalised] == [1000.0, 1200.0]
    assert stats.valid == 2


def test_forecast_unaligned_and_invalid_records_are_skipped():
    start = utc(2026, 1, 1, 0, 0)
    records = [
        windfor_row(start, utc(2026, 1, 1, 7, 30), 1000),
        windfor_row(start + timedelta(minutes=30), utc(2026, 1, 1, 7, 30), 1000),
        windfor_row(start + timedelta(hours=1), utc(2026, 1, 1, 7, 30), None),
    ]
    normalised, stats = normalize_forecast_records(records)
    assert len(normalised) == 1
    assert stats.skipped_unaligned == 1
    assert stats.skipped_invalid_generation == 1


def test_forecast_exact_duplicate_is_collapsed():
    start = utc(2026, 1, 1, 0, 0)
    row = windfor_row(start, utc(2026, 1, 1, 7, 30), 1000)
    normalised, stats = normalize_forecast_records([row, dict(row)])
    assert len(normalised) == 1
    assert stats.duplicate_exact == 1
