from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis as fakeredis
from fakeredis import FakeServer
import pytest

from app.services.cache_manager import CacheManager
from app.services.reddit_client import RedditPost


def _build_post(subreddit: str = "python") -> RedditPost:
    return RedditPost(
        id="abc123",
        title="Test Post",
        selftext="Body",
        score=10,
        num_comments=2,
        created_utc=1700000000.0,
        subreddit=subreddit,
        author="tester",
        url="https://reddit.com/test",
        permalink="/r/python/comments/abc123",
    )


@pytest.mark.asyncio
async def test_set_and_get_cached_posts() -> None:
    client = fakeredis.FakeRedis(server=FakeServer())
    manager = CacheManager(client)
    post = _build_post()

    await manager.set_cached_posts("python", [post])
    cached = await manager.get_cached_posts("python")

    assert cached is not None
    assert len(cached) == 1
    assert cached[0].id == "abc123"


@pytest.mark.asyncio
async def test_get_cached_posts_returns_none_when_stale() -> None:
    client = fakeredis.FakeRedis(server=FakeServer())
    manager = CacheManager(client)
    post = _build_post()

    await manager.set_cached_posts("python", [post])
    raw = await client.get("reddit:posts:python")
    assert raw is not None

    decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    payload = json.loads(decoded)
    old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    payload["cached_at"] = old_timestamp
    await client.set("reddit:posts:python", json.dumps(payload))

    assert await manager.get_cached_posts("python") is None


@pytest.mark.asyncio
async def test_calculate_cache_hit_rate() -> None:
    client = fakeredis.FakeRedis(server=FakeServer())
    manager = CacheManager(client)
    post = _build_post()

    await manager.set_cached_posts("python", [post])
    hit_rate = await manager.calculate_cache_hit_rate(["python", "golang"])
    assert hit_rate == pytest.approx(0.5)
