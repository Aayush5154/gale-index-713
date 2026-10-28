"""Generate the synthetic fixture dataset used only for offline demonstration.

The output is explicitly labelled synthetic.  It intentionally includes edge
cases: a non-WIND row, an invalid value, a revised actual, a missing actual
half-hour, a missing forecast hour, a duplicate forecast publication and a
zero/near-zero actual for MAPE handling.

Run from the backend directory:
    python scripts/generate_fixtures.py
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def hourly_shape(hour: datetime) -> float:
    """Deterministic, plausible GB wind shape in MW."""
    t = (hour - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds() / 3600.0
    base = 9_500 + 3_200 * math.sin(2 * math.pi * t / 72.0) + 1_600 * math.sin(2 * math.pi * t / 19.0 + 0.7)
    return max(350.0, base)


def actual_mw(hour: datetime) -> float:
    rng = random.Random(f"actual-{hour.isoformat()}")
    return max(0.0, hourly_shape(hour) + rng.uniform(-420, 420))


def forecast_mw(hour: datetime, publish: datetime) -> float:
    age = max(0.0, (hour - publish).total_seconds() / 3600.0)
    rng = random.Random(f"forecast-{hour.isoformat()}-{publish.isoformat()}")
    bias = 350 + 18 * age
    return max(0.0, hourly_shape(hour) + bias + rng.uniform(-700, 700))


def iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_actuals() -> list[dict]:
    records: list[dict] = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(31 * 48):
        stamp = start + timedelta(minutes=30 * index)
        settlement_date = stamp.date().isoformat()
        settlement_period = (stamp.hour * 2) + (1 if stamp.minute == 30 else 0) + 1
        value = round(actual_mw(stamp), 1)

        if stamp == datetime(2026, 1, 12, 3, 30, tzinfo=UTC):
            continue  # missing half-hour -> incomplete hourly actual
        if stamp == datetime(2026, 1, 6, 6, 0, tzinfo=UTC):
            continue  # replaced below by an invalid generation record
        if stamp == datetime(2026, 1, 20, 2, 0, tzinfo=UTC):
            value = 0.0
        if stamp == datetime(2026, 1, 20, 2, 30, tzinfo=UTC):
            value = 0.0
        if stamp == datetime(2026, 1, 20, 3, 0, tzinfo=UTC):
            value = 0.0
        if stamp == datetime(2026, 1, 20, 3, 30, tzinfo=UTC):
            value = 1.0

        records.append(
            {
                "dataset": "FUELHH",
                "publishTime": iso(stamp + timedelta(minutes=30)),
                "startTime": iso(stamp),
                "settlementDate": settlement_date,
                "settlementPeriod": settlement_period,
                "fuelType": "WIND",
                "generation": value,
            }
        )

        # One revised actual: a later publication supersedes the first value.
        if stamp == datetime(2026, 1, 15, 12, 0, tzinfo=UTC):
            records.append(
                {
                    "dataset": "FUELHH",
                    "publishTime": iso(stamp + timedelta(hours=6)),
                    "startTime": iso(stamp),
                    "settlementDate": settlement_date,
                    "settlementPeriod": settlement_period,
                    "fuelType": "WIND",
                    "generation": round(value + 120.0, 1),
                }
            )

    # A non-WIND row proves in-code filtering, and an invalid value proves safe parsing.
    records.append(
        {
            "dataset": "FUELHH",
            "publishTime": iso(datetime(2026, 1, 5, 12, 30, tzinfo=UTC)),
            "startTime": iso(datetime(2026, 1, 5, 12, 0, tzinfo=UTC)),
            "settlementDate": "2026-01-05",
            "settlementPeriod": 25,
            "fuelType": "NUCLEAR",
            "generation": 5000,
        }
    )
    records.append(
        {
            "dataset": "FUELHH",
            "publishTime": iso(datetime(2026, 1, 6, 6, 30, tzinfo=UTC)),
            "startTime": iso(datetime(2026, 1, 6, 6, 0, tzinfo=UTC)),
            "settlementDate": "2026-01-06",
            "settlementPeriod": 13,
            "fuelType": "WIND",
            "generation": None,
        }
    )
    return records


def generate_forecasts() -> list[dict]:
    records: list[dict] = []
    publication_times = [(2, 30), (4, 30), (7, 30), (9, 30), (11, 30), (15, 30), (18, 30), (22, 30)]
    day = datetime(2025, 12, 28, tzinfo=UTC)
    end = datetime(2026, 1, 31, tzinfo=UTC)

    while day < end:
        for hour, minute in publication_times:
            publish = day + timedelta(hours=hour, minutes=minute)
            publish_hour = publish.replace(minute=0, second=0, microsecond=0)
            for offset in range(-25, 48):
                target = publish_hour + timedelta(hours=offset)
                if target < datetime(2025, 12, 28, tzinfo=UTC) or target >= datetime(2026, 2, 2, tzinfo=UTC):
                    continue
                if target == datetime(2026, 1, 10, 5, 0, tzinfo=UTC):
                    continue  # missing forecast for this delivery hour
                records.append(
                    {
                        "dataset": "WINDFOR",
                        "publishTime": iso(publish),
                        "startTime": iso(target),
                        "generation": round(forecast_mw(target, publish), 1),
                    }
                )
        day += timedelta(days=1)

    # Duplicate eligible publication for one hour, with conflicting values.
    duplicate_target = datetime(2026, 1, 16, 12, 0, tzinfo=UTC)
    duplicate_publish = datetime(2026, 1, 15, 7, 30, tzinfo=UTC)
    records.append(
        {
            "dataset": "WINDFOR",
            "publishTime": iso(duplicate_publish),
            "startTime": iso(duplicate_target),
            "generation": round(forecast_mw(duplicate_target, duplicate_publish) + 450, 1),
        }
    )
    return records


def write(name: str, note: str, records: list[dict]) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    payload = {
        "synthetic": True,
        "note": note,
        "data": records,
    }
    path = FIXTURES / name
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    print(f"wrote {path} ({len(records)} records, {path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    write(
        "fuelhh_wind.json",
        "SYNTHETIC fixture for offline demonstration only. Not Elexon observations.",
        generate_actuals(),
    )
    write(
        "windfor.json",
        "SYNTHETIC fixture for offline demonstration only. Not Elexon observations.",
        generate_forecasts(),
    )
