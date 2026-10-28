from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.cache import CacheStats
from app.core.errors import UpstreamError
from app.services.elexon_client import FetchResult


class StaticSource:
    """In-memory data source used by API tests; no network access."""

    def __init__(
        self,
        actual_records: list[dict[str, Any]],
        forecast_records: list[dict[str, Any]],
        *,
        fail: bool = False,
        mode: str = "fixture",
    ) -> None:
        self.actual_records = actual_records
        self.forecast_records = forecast_records
        self.fail = fail
        self.mode = mode
        self.closed = False
        self.actual_calls = 0
        self.forecast_calls = 0

    async def fetch_actuals(self, start: date, end: date) -> FetchResult:
        self.actual_calls += 1
        if self.fail:
            raise UpstreamError("Simulated upstream outage.")
        return FetchResult(records=self.actual_records, chunks_requested=1, source=self.mode)

    async def fetch_forecasts(self, publish_from: datetime, publish_to: datetime) -> FetchResult:
        self.forecast_calls += 1
        if self.fail:
            raise UpstreamError("Simulated upstream outage.")
        return FetchResult(records=self.forecast_records, chunks_requested=1, source=self.mode)

    def dependency_status(self) -> dict[str, Any]:
        return {
            "name": "Test source",
            "configured": True,
            "status": "unavailable" if self.fail else "fixture",
            "last_success_at": None if self.fail else "2026-01-01T00:00:00+00:00",
            "last_error": "Simulated outage" if self.fail else None,
            "last_error_at": "2026-01-01T00:00:00+00:00" if self.fail else None,
        }

    def source_info(self) -> dict[str, Any]:
        return {
            "name": "Test fixture source",
            "mode": self.mode,
            "is_synthetic": True,
            "base_url": None,
            "documentation_url": "https://bmrs.elexon.co.uk/api-documentation/guidance",
        }

    @property
    def cache_stats(self) -> CacheStats:
        return CacheStats(size=0, max_entries=0, ttl_seconds=0)

    async def close(self) -> None:
        self.closed = True


def two_day_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """48 half-hours and two publication versions with a post-cutoff distractor."""
    actuals: list[dict[str, Any]] = []
    for day in (1, 2):
        for half_hour in range(48):
            hour = half_hour // 2
            minute = 30 if half_hour % 2 else 0
            start = datetime(2026, 1, day, hour, minute)
            actuals.append(
                {
                    "dataset": "FUELHH",
                    "publishTime": start.replace(day=day, hour=min(hour + 1, 23)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "settlementDate": f"2026-01-{day:02d}",
                    "settlementPeriod": half_hour + 1,
                    "fuelType": "WIND",
                    "generation": 10000,
                }
            )

    forecasts: list[dict[str, Any]] = []
    # Version used for 1 January, published before the 31 December 09:20 cutoff.
    for day in (1, 2):
        for hour in range(24):
            start = datetime(2026, 1, day, hour)
            forecasts.append(
                {
                    "dataset": "WINDFOR",
                    "publishTime": "2025-12-31T07:30:00Z",
                    "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "generation": 10500,
                }
            )
    # Version used for 2 January, published before the 1 January 09:20 cutoff.
    for day in (2, 3):
        for hour in range(24):
            start = datetime(2026, 1, day, hour)
            forecasts.append(
                {
                    "dataset": "WINDFOR",
                    "publishTime": "2026-01-01T07:30:00Z",
                    "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "generation": 11000,
                }
            )
    # Distractor published after the 2 January cutoff; must never be selected.
    for hour in range(24):
        start = datetime(2026, 1, 2, hour)
        forecasts.append(
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T11:30:00Z",
                "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "generation": 99999,
            }
        )
    return actuals, forecasts
