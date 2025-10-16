from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest

from app.services.cache_metrics import CacheMetrics, RedisLikeMetrics


class _FakeRedis(RedisLikeMetrics):  # type: ignore[misc]
    def __init__(self) -> None:
        self.store: Dict[str, int] = {}
        self.ttl: Dict[str, int] = {}

    def incrby(self, name: str, amount: int = 1) -> int:  # type: ignore[override]
        self.store[name] = self.store.get(name, 0) + amount
        return self.store[name]

    def expire(self, name: str, time: int) -> bool | int | None:  # type: ignore[override]
        # For tests we just record TTL without enforcing it
        self.ttl[name] = time
        return True

    def get(self, name: str) -> bytes | str | None:  # type: ignore[override]
        if name not in self.store:
            return None
        return str(self.store[name])


@pytest.mark.asyncio
async def test_initial_rate_zero_when_no_data() -> None:
    metrics = CacheMetrics(redis_client=_FakeRedis())
    rate = await metrics.calculate_hit_rate(window_minutes=5)
    assert rate == 0.0


@pytest.mark.asyncio
async def test_record_and_calculate_rate_for_recent_minute() -> None:
    fake = _FakeRedis()
    metrics = CacheMetrics(redis_client=fake)

    now = datetime(2025, 10, 15, 10, 30, tzinfo=timezone.utc)

    # 3 hits, 1 miss in current minute
    await metrics.record_hit(now=now)
    await metrics.record_hit(now=now)
    await metrics.record_hit(now=now)
    await metrics.record_miss(now=now)

    # old data outside window should be ignored
    old = now - timedelta(minutes=10)
    await metrics.record_miss(now=old)

    rate = await metrics.calculate_hit_rate(window_minutes=1, now=now)
    assert rate == pytest.approx(0.75, rel=1e-6)


@pytest.mark.asyncio
async def test_window_aggregation_across_multiple_minutes() -> None:
    fake = _FakeRedis()
    metrics = CacheMetrics(redis_client=fake)

    now = datetime(2025, 10, 15, 10, 30, tzinfo=timezone.utc)
    prev = now - timedelta(minutes=1)

    # prev minute: 2 hits, 2 misses
    await metrics.record_hit(now=prev)
    await metrics.record_hit(now=prev)
    await metrics.record_miss(now=prev)
    await metrics.record_miss(now=prev)

    # current minute: 1 hit
    await metrics.record_hit(now=now)

    hits, misses = await metrics.get_counts(window_minutes=2, now=now)
    assert hits == 3 and misses == 2

    rate = await metrics.calculate_hit_rate(window_minutes=2, now=now)
    assert rate == pytest.approx(3 / 5, rel=1e-6)

