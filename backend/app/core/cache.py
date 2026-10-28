"""Bounded, TTL-based in-memory cache with request coalescing.

The cache is intentionally small and process-local.  It exists to avoid
re-downloading the same Elexon chunks on every page request and to coalesce
concurrent cold requests.  It is not a source of truth: entries expire and the
process can be restarted at any time.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    expired: int = 0
    evictions: int = 0
    inflight_coalesced: int = 0
    size: int = 0
    max_entries: int = 0
    ttl_seconds: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "expired": self.expired,
            "evictions": self.evictions,
            "inflight_coalesced": self.inflight_coalesced,
            "size": self.size,
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
        }


class TTLCache(Generic[K, V]):
    def __init__(self, *, max_entries: int, ttl_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._clock = clock
        self._data: OrderedDict[K, _Entry[V]] = OrderedDict()
        self._inflight: dict[K, asyncio.Task[V]] = {}
        self._lock = asyncio.Lock()
        self._stats = CacheStats(max_entries=max_entries, ttl_seconds=ttl_seconds)

    async def get_or_create(self, key: K, factory: Callable[[], Awaitable[V]]) -> V:
        """Return a cached value or run ``factory`` once for concurrent callers."""
        async with self._lock:
            now = self._clock()
            entry = self._data.get(key)
            if entry is not None:
                if entry.expires_at > now:
                    self._data.move_to_end(key)
                    self._stats.hits += 1
                    self._stats.size = len(self._data)
                    return entry.value
                self._data.pop(key, None)
                self._stats.expired += 1

            existing = self._inflight.get(key)
            if existing is not None:
                self._stats.inflight_coalesced += 1
                owner = False
                task = existing
            else:
                self._stats.misses += 1
                task = asyncio.create_task(factory())
                self._inflight[key] = task
                owner = True

        if not owner:
            return await task

        try:
            value = await task
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

        async with self._lock:
            self._data[key] = _Entry(value=value, expires_at=self._clock() + self._ttl)
            self._data.move_to_end(key)
            while len(self._data) > self._max_entries:
                self._data.popitem(last=False)
                self._stats.evictions += 1
            self._stats.size = len(self._data)
        return value

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()
            self._stats.size = 0

    @property
    def stats(self) -> CacheStats:
        self._stats.size = len(self._data)
        return self._stats
