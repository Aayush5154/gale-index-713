from __future__ import annotations

import asyncio

import pytest

from app.core.cache import TTLCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.asyncio
async def test_cache_hit_and_miss():
    clock = FakeClock()
    cache: TTLCache[str, str] = TTLCache(max_entries=4, ttl_seconds=10, clock=clock)
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        return "value"

    assert await cache.get_or_create("a", factory) == "value"
    assert await cache.get_or_create("a", factory) == "value"
    assert calls == 1
    assert cache.stats.misses == 1
    assert cache.stats.hits == 1


@pytest.mark.asyncio
async def test_cache_expiry():
    clock = FakeClock()
    cache: TTLCache[str, str] = TTLCache(max_entries=4, ttl_seconds=10, clock=clock)
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        return f"value-{calls}"

    assert await cache.get_or_create("a", factory) == "value-1"
    clock.now = 11
    assert await cache.get_or_create("a", factory) == "value-2"
    assert calls == 2
    assert cache.stats.expired == 1


@pytest.mark.asyncio
async def test_cache_evicts_least_recently_used():
    clock = FakeClock()
    cache: TTLCache[str, int] = TTLCache(max_entries=2, ttl_seconds=10, clock=clock)
    values = {"a": 1, "b": 2, "c": 3}

    for key in values:
        await cache.get_or_create(key, lambda key=key: _value(values[key]))
    assert cache.stats.size == 2
    assert cache.stats.evictions == 1


async def _value(value: int) -> int:
    return value


@pytest.mark.asyncio
async def test_concurrent_misses_are_coalesced():
    cache: TTLCache[str, str] = TTLCache(max_entries=4, ttl_seconds=10)
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return "value"

    results = await asyncio.gather(*[cache.get_or_create("same", factory) for _ in range(8)])
    assert results == ["value"] * 8
    assert calls == 1
    assert cache.stats.inflight_coalesced == 7


@pytest.mark.asyncio
async def test_failed_factory_is_not_cached():
    cache: TTLCache[str, str] = TTLCache(max_entries=4, ttl_seconds=10)
    calls = 0

    async def failing() -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await cache.get_or_create("key", failing)
    assert cache.stats.size == 0
    assert calls == 1
