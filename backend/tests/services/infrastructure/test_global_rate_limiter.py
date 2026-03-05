from __future__ import annotations

import asyncio

import pytest

try:
    import fakeredis.aioredis as fakeredis  # type: ignore
except Exception:  # pragma: no cover - CI fallback if fakeredis not available
    fakeredis = None  # type: ignore

from app.services.infrastructure.global_rate_limiter import GlobalRateLimiter


@pytest.mark.asyncio
async def test_global_rate_limiter_simple_window() -> None:
    if fakeredis is None:
        pytest.skip("fakeredis not available")

    r = fakeredis.FakeRedis()
    limiter = GlobalRateLimiter(r, limit=3, window_seconds=2, client_id="test")

    # first three pass
    assert await limiter.acquire() == 0
    assert await limiter.acquire() == 0
    assert await limiter.acquire() == 0

    # fourth should be throttled
    wait = await limiter.acquire()
    assert wait >= 1

    # after window, should pass again
    await asyncio.sleep(2)
    assert await limiter.acquire() == 0

