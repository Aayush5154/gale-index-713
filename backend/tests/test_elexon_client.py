from __future__ import annotations

from datetime import date, datetime, timezone

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import UpstreamError, UpstreamResponseError
from app.services.elexon_client import ElexonClient, iter_date_chunks, iter_datetime_chunks

UTC = timezone.utc


def settings(**overrides) -> Settings:
    values = {
        "elexon_max_retries": 1,
        "elexon_chunk_days": 6,
        "cache_ttl_seconds": 60,
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(**values)


def make_client(handler, **overrides) -> tuple[ElexonClient, httpx.AsyncClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    transport = httpx.MockTransport(recording_handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://example.test/api/v1")
    client = ElexonClient(settings(**overrides), http_client=http)
    monkeypatch_backoff(client)
    return client, http, requests


def monkeypatch_backoff(client: ElexonClient) -> None:
    client._backoff = lambda attempt: 0.0  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_successful_actuals_request_is_cached():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "dataset": "FUELHH",
                    "publishTime": "2026-01-01T00:30:00Z",
                    "startTime": "2026-01-01T00:00:00Z",
                    "fuelType": "WIND",
                    "generation": 1000,
                }
            ],
        )

    client, http, requests = make_client(handler)
    try:
        first = await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
        second = await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
        assert len(first.records) == 1
        assert second.records == first.records
        assert len(requests) == 1
        assert client.cache_stats.hits == 1
        assert first.chunks_requested == 1
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_data_array_wrapper_is_accepted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"dataset": "WINDFOR"}]})

    client, http, _ = make_client(handler)
    try:
        result = await client.fetch_forecasts(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC))
        assert len(result.records) == 1
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_server_error_is_retried_then_succeeds():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, text="temporary")
        return httpx.Response(200, json=[])

    client, http, requests = make_client(handler)
    try:
        result = await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
        assert result.records == []
        assert attempts == 2
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_rate_limit_is_retried_and_reported():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, headers={"Retry-After": "0"}, text="slow down")

    client, http, _ = make_client(handler)
    try:
        with pytest.raises(UpstreamError) as exc_info:
            await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
        assert exc_info.value.details["status"] == 429
        assert attempts == 2
        assert "rate limit" in exc_info.value.message.lower()
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_client_error_is_not_retried():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"errors": {"": ["range too large"]}})

    client, http, _ = make_client(handler)
    try:
        with pytest.raises(UpstreamError) as exc_info:
            await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
        assert exc_info.value.details["status"] == 400
        assert attempts == 1
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_malformed_json_is_reported():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})

    client, http, _ = make_client(handler)
    try:
        with pytest.raises(UpstreamResponseError):
            await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_unexpected_payload_shape_is_reported():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": []})

    client, http, _ = make_client(handler)
    try:
        with pytest.raises(UpstreamResponseError):
            await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_timeout_is_wrapped_as_upstream_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client, http, _ = make_client(handler)
    try:
        with pytest.raises(UpstreamError):
            await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_chunking_never_exceeds_seven_days_and_uses_wind_filter():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client, http, requests = make_client(handler)
    try:
        result = await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 15))
        assert result.chunks_requested == 3
        assert len(requests) == 3
        for request in requests:
            params = request.url.params
            start = date.fromisoformat(params["settlementDateFrom"])
            end = date.fromisoformat(params["settlementDateTo"])
            assert (end - start).days <= 6
            assert params["fuelType"] == "WIND"
            assert request.url.path == "/api/v1/datasets/FUELHH/stream"
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_forecast_chunking_and_publish_parameters():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client, http, requests = make_client(handler)
    try:
        result = await client.fetch_forecasts(
            datetime(2025, 12, 28, 9, 20, tzinfo=UTC),
            datetime(2026, 1, 10, 9, 20, tzinfo=UTC),
        )
        assert result.chunks_requested == 3
        for request in requests:
            assert "publishDateTimeFrom" in request.url.params
            assert "publishDateTimeTo" in request.url.params
            assert request.url.path == "/api/v1/datasets/WINDFOR/stream"
    finally:
        await http.aclose()


def test_date_chunk_iterator_is_inclusive_and_bounded():
    chunks = list(iter_date_chunks(date(2026, 1, 1), date(2026, 1, 15), chunk_days=6))
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 6))
    assert chunks[-1][1] == date(2026, 1, 15)
    assert all((end - start).days <= 6 for start, end in chunks)


def test_datetime_chunk_iterator_is_bounded():
    chunks = list(
        iter_datetime_chunks(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 20, tzinfo=UTC), chunk_days=6
        )
    )
    assert all((end - start).total_seconds() <= 7 * 86400 for start, end in chunks)
    assert chunks[0][0] == datetime(2026, 1, 1, tzinfo=UTC)
    assert chunks[-1][1] == datetime(2026, 1, 20, tzinfo=UTC)
