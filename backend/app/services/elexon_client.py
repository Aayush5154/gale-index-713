"""Elexon Insights API client with chunking, retries and a bounded cache.

The documented dataset endpoints cap a request at seven days, so both
datasets are retrieved in six-day chunks.  WINDFOR supports only publication
time filters, which is why the analysis derives a publication window from the
decision cut-offs rather than downloading the full archive.

Reference: https://bmrs.elexon.co.uk/api-documentation/guidance
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

import httpx

from app.core.cache import CacheStats, TTLCache
from app.core.config import Settings
from app.core.errors import UpstreamError, UpstreamResponseError

logger = logging.getLogger(__name__)
UTC = timezone.utc


@dataclass(frozen=True)
class FetchResult:
    records: list[Mapping[str, Any]]
    chunks_requested: int
    source: str


class WindDataSource(Protocol):
    async def fetch_actuals(self, start: date, end: date) -> FetchResult: ...

    async def fetch_forecasts(self, publish_from: datetime, publish_to: datetime) -> FetchResult: ...

    def dependency_status(self) -> dict[str, Any]: ...

    def source_info(self) -> dict[str, Any]: ...

    @property
    def cache_stats(self) -> CacheStats: ...

    async def close(self) -> None: ...


def iter_date_chunks(start: date, end: date, chunk_days: int = 6):
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def iter_datetime_chunks(start: datetime, end: datetime, chunk_days: int = 6):
    current = start
    step = timedelta(days=chunk_days)
    while current < end:
        chunk_end = min(current + step, end)
        yield current, chunk_end
        current = chunk_end


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
        cache: TTLCache[str, list[Mapping[str, Any]]] | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        timeout = httpx.Timeout(
            connect=settings.elexon_connect_timeout_seconds,
            read=settings.elexon_timeout_seconds,
            write=settings.elexon_timeout_seconds,
            pool=settings.elexon_connect_timeout_seconds,
        )
        self._http = http_client or httpx.AsyncClient(
            base_url=settings.elexon_base_url,
            timeout=timeout,
            headers={
                "User-Agent": settings.elexon_user_agent,
                "Accept": "application/json",
            },
            follow_redirects=True,
        )
        self._cache = cache or TTLCache(
            max_entries=settings.cache_max_entries,
            ttl_seconds=settings.cache_ttl_seconds,
        )
        self._semaphore = asyncio.Semaphore(settings.elexon_concurrency)
        self._last_success_at: datetime | None = None
        self._last_error: str | None = None
        self._last_error_at: datetime | None = None

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    @property
    def cache_stats(self) -> CacheStats:
        return self._cache.stats

    def source_info(self) -> dict[str, Any]:
        return {
            "name": "Elexon Insights Solution (BMRS)",
            "mode": "live",
            "is_synthetic": False,
            "base_url": self._settings.elexon_base_url,
            "documentation_url": "https://bmrs.elexon.co.uk/api-documentation/guidance",
        }

    def dependency_status(self) -> dict[str, Any]:
        if self._last_error and self._last_success_at is None:
            status = "unavailable"
        elif self._last_error:
            status = "degraded"
        elif self._last_success_at:
            status = "ok"
        else:
            status = "not_yet_called"
        return {
            "name": "Elexon Insights API",
            "configured": True,
            "status": status,
            "last_success_at": self._last_success_at.isoformat() if self._last_success_at else None,
            "last_error": self._last_error,
            "last_error_at": self._last_error_at.isoformat() if self._last_error_at else None,
        }

    async def fetch_actuals(self, start: date, end: date) -> FetchResult:
        chunks = list(iter_date_chunks(start, end, self._settings.elexon_chunk_days))
        results = await asyncio.gather(
            *[
                self._get_cached(
                    "/datasets/FUELHH/stream",
                    {
                        "settlementDateFrom": chunk_start.isoformat(),
                        "settlementDateTo": chunk_end.isoformat(),
                        "fuelType": "WIND",
                    },
                    cache_key=f"FUELHH:{chunk_start}:{chunk_end}",
                )
                for chunk_start, chunk_end in chunks
            ]
        )
        records = [record for chunk in results for record in chunk]
        logger.info("FUELHH fetch complete: %s chunks, %s records", len(chunks), len(records))
        return FetchResult(records=records, chunks_requested=len(chunks), source="live")

    async def fetch_forecasts(self, publish_from: datetime, publish_to: datetime) -> FetchResult:
        chunks = list(iter_datetime_chunks(publish_from, publish_to, self._settings.elexon_chunk_days))
        results = await asyncio.gather(
            *[
                self._get_cached(
                    "/datasets/WINDFOR/stream",
                    {
                        "publishDateTimeFrom": _format_utc(chunk_start),
                        "publishDateTimeTo": _format_utc(chunk_end),
                    },
                    cache_key=f"WINDFOR:{chunk_start.isoformat()}:{chunk_end.isoformat()}",
                )
                for chunk_start, chunk_end in chunks
            ]
        )
        records = [record for chunk in results for record in chunk]
        logger.info("WINDFOR fetch complete: %s chunks, %s records", len(chunks), len(records))
        return FetchResult(records=records, chunks_requested=len(chunks), source="live")

    async def _get_cached(
        self,
        path: str,
        params: dict[str, str],
        *,
        cache_key: str,
    ) -> list[Mapping[str, Any]]:
        return await self._cache.get_or_create(
            cache_key,
            lambda: self._request_json(path, params),
        )

    async def _request_json(
        self,
        path: str,
        params: dict[str, str],
    ) -> list[Mapping[str, Any]]:
        last_exception: Exception | None = None
        attempts = self._settings.elexon_max_retries + 1

        for attempt in range(attempts):
            try:
                async with self._semaphore:
                    response = await self._http.get(path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exception = exc
                logger.warning(
                    "Elexon request failed (%s attempt %s/%s): %s",
                    path,
                    attempt + 1,
                    attempts,
                    type(exc).__name__,
                )
                if attempt + 1 < attempts:
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                self._record_error("The Elexon API could not be reached.")
                raise UpstreamError(
                    "The Elexon API could not be reached. Please retry shortly."
                ) from exc

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                logger.warning(
                    "Elexon returned HTTP %s for %s (attempt %s/%s)",
                    response.status_code,
                    path,
                    attempt + 1,
                    attempts,
                )
                if attempt + 1 < attempts:
                    delay = self._backoff(attempt)
                    if retry_after and retry_after.isdigit():
                        delay = min(max(float(retry_after), 0.5), 10.0)
                    await asyncio.sleep(delay)
                    continue
                message = (
                    "The Elexon API rate limit was reached. Please retry shortly."
                    if response.status_code == 429
                    else "The Elexon API is temporarily unavailable."
                )
                self._record_error(f"HTTP {response.status_code}")
                raise UpstreamError(message, details={"status": response.status_code})

            if response.status_code >= 400:
                self._record_error(f"HTTP {response.status_code}")
                logger.warning(
                    "Elexon rejected %s with HTTP %s: %s",
                    path,
                    response.status_code,
                    response.text[:300],
                )
                raise UpstreamError(
                    "The Elexon API rejected the data request. Check the requested period.",
                    details={"status": response.status_code},
                )

            try:
                payload = response.json()
            except (json.JSONDecodeError, ValueError) as exc:
                self._record_error("Malformed JSON response")
                raise UpstreamResponseError(
                    "The Elexon API returned malformed JSON."
                ) from exc

            try:
                records = self._extract_records(payload)
            except UpstreamResponseError:
                self._record_error("Invalid response structure")
                raise
            self._last_success_at = datetime.now(UTC)
            self._last_error = None
            self._last_error_at = None
            return records

        self._record_error("Retries exhausted")
        raise UpstreamError("The Elexon API request failed.") from last_exception

    @staticmethod
    def _extract_records(payload: object) -> list[Mapping[str, Any]]:
        if isinstance(payload, list):
            raw_records = payload
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            raw_records = payload["data"]
        else:
            raise UpstreamResponseError(
                "The Elexon API response did not contain a data array."
            )

        if not all(isinstance(record, Mapping) for record in raw_records):
            raise UpstreamResponseError(
                "The Elexon API response contained records with an unexpected shape."
            )
        return raw_records

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(0.5 * (2**attempt) + random.uniform(0, 0.25), 5.0)

    def _record_error(self, message: str) -> None:
        self._last_error = message
        self._last_error_at = datetime.now(UTC)


class FixtureClient:
    """Clearly-labelled synthetic fixture source for offline evaluation.

    Fixture mode never calls Elexon.  The UI and metadata expose ``is_synthetic``
    so that generated values are not mistaken for verified observations.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._actuals: list[Mapping[str, Any]] | None = None
        self._forecasts: list[Mapping[str, Any]] | None = None
        self._last_success_at = datetime.now(UTC)

    async def close(self) -> None:  # pragma: no cover - symmetry with live client
        return None

    @property
    def cache_stats(self) -> CacheStats:
        return CacheStats(size=0, max_entries=0, ttl_seconds=0)

    def source_info(self) -> dict[str, Any]:
        return {
            "name": "Synthetic fixture dataset",
            "mode": "fixture",
            "is_synthetic": True,
            "base_url": None,
            "documentation_url": "https://bmrs.elexon.co.uk/api-documentation/guidance",
            "note": (
                "Fixture mode is for offline demonstration and tests only. Values are synthetic "
                "and must not be presented as Elexon observations."
            ),
        }

    def dependency_status(self) -> dict[str, Any]:
        return {
            "name": "Fixture data source",
            "configured": True,
            "status": "fixture",
            "last_success_at": self._last_success_at.isoformat(),
            "last_error": None,
            "last_error_at": None,
        }

    def _load(self, filename: str) -> list[Mapping[str, Any]]:
        path = self._settings.fixture_dir / filename
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError as exc:
            raise UpstreamError(
                "Fixture data is not available. Check FIXTURE_DIR or use DATA_MODE=live."
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise UpstreamResponseError("Fixture data could not be parsed.") from exc

        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            payload = payload["data"]
        if not isinstance(payload, list) or not all(isinstance(item, Mapping) for item in payload):
            raise UpstreamResponseError("Fixture data has an unexpected shape.")
        return payload

    async def fetch_actuals(self, start: date, end: date) -> FetchResult:
        if self._actuals is None:
            self._actuals = self._load("fuelhh_wind.json")
        start_dt = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        records = []
        for record in self._actuals:
            try:
                stamp = datetime.fromisoformat(str(record["startTime"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if start_dt <= stamp.astimezone(UTC) < end_dt:
                records.append(record)
        return FetchResult(records=records, chunks_requested=1, source="fixture")

    async def fetch_forecasts(self, publish_from: datetime, publish_to: datetime) -> FetchResult:
        if self._forecasts is None:
            self._forecasts = self._load("windfor.json")
        records = []
        for record in self._forecasts:
            try:
                stamp = datetime.fromisoformat(str(record["publishTime"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if publish_from <= stamp.astimezone(UTC) <= publish_to:
                records.append(record)
        return FetchResult(records=records, chunks_requested=1, source="fixture")


def create_data_source(settings: Settings) -> WindDataSource:
    if settings.is_fixture_mode:
        return FixtureClient(settings)
    return ElexonClient(settings)
