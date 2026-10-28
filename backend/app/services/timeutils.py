"""Timezone-aware date/time helpers used across the analysis pipeline.

Internal timestamps are always timezone-aware UTC.  UK market dates and
timestamps are rendered in Europe/London by the API and the UI.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.errors import InvalidQueryError

UTC = timezone.utc


def parse_iso_datetime(value: object) -> datetime:
    """Parse an ISO-8601 timestamp and normalise it to UTC.

    Naive timestamps are treated as UTC.  Elexon returns UTC timestamps with a
    trailing ``Z``; accepting naive values keeps fixture and test handling
    straightforward.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO-8601 timestamp: {value!r}") from exc
    else:
        raise ValueError("Timestamp is missing or not a string")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidQueryError(
            f"Invalid date '{value}'. Expected YYYY-MM-DD.",
            details={"field": "date"},
        ) from exc


def parse_cutoff_time(value: str) -> time:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise InvalidQueryError(
            f"Invalid cutoff time '{value}'. Expected HH:MM (24-hour clock).",
            details={"field": "cutoff_time"},
        ) from exc
    return parsed.replace(tzinfo=None, second=0, microsecond=0)


def local_midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz)


def local_day_bounds(start: date, end: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Return the UTC half-open bounds covering local calendar days."""
    return local_midnight(start, tz).astimezone(UTC), local_midnight(end + timedelta(days=1), tz).astimezone(UTC)


def hourly_starts(start: datetime, end: datetime) -> list[datetime]:
    if end <= start:
        return []
    seconds = (end - start).total_seconds()
    if seconds % 3600 != 0:
        # The delivery window is always whole hours for Europe/London, but a
        # defensive floor avoids silently drifting the last interval.
        seconds -= seconds % 3600
    count = int(seconds // 3600)
    return [start + timedelta(hours=i) for i in range(count)]


def cutoff_for_delivery_day(day: date, cutoff_time: time, tz: ZoneInfo) -> datetime:
    """Cut-off on D-1 at the configured London local time, returned in UTC."""
    previous_day = day - timedelta(days=1)
    local = datetime.combine(previous_day, cutoff_time, tzinfo=tz)
    return local.astimezone(UTC)


def cutoff_from_input(value: datetime, tz: ZoneInfo) -> datetime:
    """Interpret a naive cutoff as London local time; normalise aware values."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    return value.astimezone(UTC)


def to_local_iso(value: datetime, tz: ZoneInfo) -> str:
    return value.astimezone(tz).isoformat(timespec="minutes")


def local_date(value: datetime, tz: ZoneInfo) -> date:
    return value.astimezone(tz).date()
