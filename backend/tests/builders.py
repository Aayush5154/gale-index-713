"""Small, explicit record builders for deterministic tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fuelhh_row(
    start: datetime,
    generation: object,
    *,
    publish: datetime | None = None,
    fuel_type: str = "WIND",
    dataset: str = "FUELHH",
    settlement_date: str | None = None,
    settlement_period: int | None = None,
) -> dict[str, object]:
    return {
        "dataset": dataset,
        "publishTime": iso(publish or start + timedelta(minutes=30)),
        "startTime": iso(start),
        "settlementDate": settlement_date or start.date().isoformat(),
        "settlementPeriod": settlement_period,
        "fuelType": fuel_type,
        "generation": generation,
    }


def windfor_row(
    start: datetime,
    publish: datetime,
    generation: object,
    *,
    dataset: str = "WINDFOR",
) -> dict[str, object]:
    return {
        "dataset": dataset,
        "publishTime": iso(publish),
        "startTime": iso(start),
        "generation": generation,
    }


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)
