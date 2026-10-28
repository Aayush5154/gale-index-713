from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from app.core.errors import InvalidQueryError
from app.services.timeutils import (
    cutoff_for_delivery_day,
    cutoff_from_input,
    hourly_starts,
    local_day_bounds,
    parse_cutoff_time,
    parse_iso_datetime,
)

UTC = timezone.utc
LDN = ZoneInfo("Europe/London")


def test_parse_iso_datetime_handles_z_offsets_and_naive_values():
    assert parse_iso_datetime("2026-01-01T00:00:00Z") == datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_iso_datetime("2026-01-01T01:00:00+01:00") == datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_iso_datetime("2026-01-01T00:00:00") == datetime(2026, 1, 1, tzinfo=UTC)


def test_parse_iso_datetime_rejects_invalid_values():
    with pytest.raises(ValueError):
        parse_iso_datetime("not-a-timestamp")
    with pytest.raises(ValueError):
        parse_iso_datetime(None)


def test_parse_cutoff_time_rejects_invalid_values():
    assert parse_cutoff_time("09:20") == time(9, 20)
    with pytest.raises(InvalidQueryError):
        parse_cutoff_time("25:61")


def test_local_day_bounds_for_january():
    start, end = local_day_bounds(date(2026, 1, 1), date(2026, 1, 1), LDN)
    assert start == datetime(2026, 1, 1, tzinfo=UTC)
    assert end == datetime(2026, 1, 2, tzinfo=UTC)


def test_hourly_starts_are_utc_hour_boundaries():
    hours = hourly_starts(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC))
    assert len(hours) == 24
    assert hours[0] == datetime(2026, 1, 1, tzinfo=UTC)
    assert hours[-1] == datetime(2026, 1, 1, 23, tzinfo=UTC)


def test_cutoff_uses_previous_london_day_in_winter():
    cutoff = cutoff_for_delivery_day(date(2026, 1, 2), time(9, 20), LDN)
    assert cutoff == datetime(2026, 1, 1, 9, 20, tzinfo=UTC)


def test_cutoff_handles_british_summer_time():
    # 30 March 2026 is BST (UTC+1), so 09:20 London is 08:20 UTC.
    cutoff = cutoff_for_delivery_day(date(2026, 3, 30), time(9, 20), LDN)
    assert cutoff == datetime(2026, 3, 29, 8, 20, tzinfo=UTC)


def test_cutoff_handles_end_of_british_summer_time():
    # 25 October 2026 is the clock-change day.  At 09:20 London the clocks have
    # already gone back to GMT, so the cut-off is 09:20 UTC.  The previous day's
    # cut-off (24 October, still BST) is 08:20 UTC.
    cutoff = cutoff_for_delivery_day(date(2026, 10, 26), time(9, 20), LDN)
    assert cutoff == datetime(2026, 10, 25, 9, 20, tzinfo=UTC)
    previous = cutoff_for_delivery_day(date(2026, 10, 25), time(9, 20), LDN)
    assert previous == datetime(2026, 10, 24, 8, 20, tzinfo=UTC)


def test_cutoff_from_naive_input_is_london_local():
    cutoff = cutoff_from_input(datetime(2026, 1, 1, 9, 20), LDN)
    assert cutoff == datetime(2026, 1, 1, 9, 20, tzinfo=UTC)
    cutoff_summer = cutoff_from_input(datetime(2026, 7, 1, 9, 20), LDN)
    assert cutoff_summer == datetime(2026, 7, 1, 8, 20, tzinfo=UTC)


def test_cutoff_from_aware_input_is_converted_to_utc():
    value = datetime(2026, 1, 1, 10, 20, tzinfo=ZoneInfo("Europe/Berlin"))
    assert cutoff_from_input(value, LDN) == datetime(2026, 1, 1, 9, 20, tzinfo=UTC)
