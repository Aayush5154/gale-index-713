"""Actual wind outturn handling.

FUELHH values are average MW over a 30-minute settlement period.  WINDFOR is
hourly, so a comparison hour is represented by the arithmetic mean of its two
half-hourly average-MW values.  This is an average of power, not an energy
conversion: no multiplication by 0.5 is applied.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from app.models.domain import ActualRecord, HourlyActual


def half_hourly_window(records: list[ActualRecord], start: datetime, end: datetime) -> list[ActualRecord]:
    return [record for record in records if start <= record.start_time < end]


def aggregate_hourly_actuals(
    records: list[ActualRecord],
    hours: list[datetime],
) -> dict[datetime, HourlyActual]:
    grouped: dict[datetime, list[ActualRecord]] = defaultdict(list)
    for record in records:
        hour = record.start_time.replace(minute=0, second=0, microsecond=0)
        grouped[hour].append(record)

    result: dict[datetime, HourlyActual] = {}
    for hour in hours:
        in_hour = sorted(grouped.get(hour, []), key=lambda r: r.start_time)
        by_start = {record.start_time: record for record in in_hour}
        expected_starts = (hour, hour + timedelta(minutes=30))
        values = tuple(by_start[stamp].generation_mw for stamp in expected_starts if stamp in by_start)
        complete = len(values) == 2 and all(stamp in by_start for stamp in expected_starts)
        result[hour] = HourlyActual(
            start_time=hour,
            generation_mw=(sum(values) / len(values)) if complete else None,
            half_hour_values=values,
            expected_half_hours=2,
        )
    return result
