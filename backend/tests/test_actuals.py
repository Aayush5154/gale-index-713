from __future__ import annotations

from datetime import timedelta

from app.services.actuals import aggregate_hourly_actuals, half_hourly_window
from app.services.normalization import normalize_actual_records
from tests.builders import fuelhh_row, utc

HOUR = utc(2026, 1, 1, 0, 0)


def normalise(rows):
    records, _ = normalize_actual_records(rows)
    return records


def test_two_half_hours_are_averaged_to_hourly_average_power():
    records = normalise(
        [
            fuelhh_row(HOUR, 10000),
            fuelhh_row(HOUR + timedelta(minutes=30), 12000),
        ]
    )
    hourly = aggregate_hourly_actuals(records, [HOUR])[HOUR]
    assert hourly.generation_mw == 11000
    assert hourly.half_hour_values == (10000.0, 12000.0)
    assert hourly.complete is True


def test_incomplete_hour_is_missing_actual():
    records = normalise([fuelhh_row(HOUR, 10000)])
    hourly = aggregate_hourly_actuals(records, [HOUR])[HOUR]
    assert hourly.generation_mw is None
    assert hourly.complete is False
    assert hourly.half_hour_values == (10000.0,)


def test_missing_half_hour_does_not_use_adjacent_hour_value():
    records = normalise(
        [
            fuelhh_row(HOUR, 10000),
            fuelhh_row(HOUR + timedelta(hours=1), 13000),
            fuelhh_row(HOUR + timedelta(hours=1, minutes=30), 15000),
        ]
    )
    hourly = aggregate_hourly_actuals(records, [HOUR, HOUR + timedelta(hours=1)])
    assert hourly[HOUR].generation_mw is None
    assert hourly[HOUR + timedelta(hours=1)].generation_mw == 14000


def test_half_hourly_window_is_half_open():
    records = normalise(
        [
            fuelhh_row(HOUR - timedelta(minutes=30), 9000),
            fuelhh_row(HOUR, 10000),
            fuelhh_row(HOUR + timedelta(minutes=30), 11000),
            fuelhh_row(HOUR + timedelta(hours=1), 12000),
        ]
    )
    window = half_hourly_window(records, HOUR, HOUR + timedelta(hours=1))
    assert [record.start_time for record in window] == [HOUR, HOUR + timedelta(minutes=30)]


def test_zero_values_are_valid_actuals():
    records = normalise(
        [
            fuelhh_row(HOUR, 0),
            fuelhh_row(HOUR + timedelta(minutes=30), 0),
        ]
    )
    hourly = aggregate_hourly_actuals(records, [HOUR])[HOUR]
    assert hourly.generation_mw == 0
    assert hourly.complete is True
