from __future__ import annotations

import logging
import time

import pytest

from app.services.crawl.data_collection_runtime import (
    DataCollectionRuntimeDeps,
    DataCollectionRuntimeInput,
    collect_posts_with_fallback,
)
from app.services.infrastructure.reddit_client import RedditPost


def _post(*, subreddit: str, created_utc: float) -> RedditPost:
    return RedditPost(
        id="p1",
        title="post",
        selftext="body",
        score=1,
        num_comments=1,
        created_utc=created_utc,
        subreddit=subreddit,
        author="alice",
        url="https://reddit.com/x",
        permalink="/r/test/comments/x",
    )


@pytest.mark.asyncio
async def test_collect_posts_with_fallback_uses_fresh_cache_without_api() -> None:
    async def _cache_get(_subreddit: str) -> list[RedditPost]:
        return [_post(subreddit="r/python", created_utc=time.time())]

    async def _cache_set(_subreddit: str, _posts) -> None:
        return None

    async def _load_empty(_subreddits, _limit: int):
        return {}

    async def _fetch(_subreddit: str, _limit: int):
        raise AssertionError("API should not be called when cache is fresh")

    result = await collect_posts_with_fallback(
        runtime_input=DataCollectionRuntimeInput(
            communities=["python"],
            limit_per_subreddit=5,
            cache_stale_hours=12,
            stale_fallback_enabled=True,
        ),
        deps=DataCollectionRuntimeDeps(
            cache_get=_cache_get,
            cache_set=_cache_set,
            load_hot_posts=_load_empty,
            load_cold_posts=_load_empty,
            fetch_subreddit_posts=_fetch,
            logger=logging.getLogger("test.data_collection_runtime"),
        ),
    )

    assert result.total_posts == 1
    assert result.cache_hits == 1
    assert result.api_calls == 0
    assert "r/python" in result.posts_by_subreddit


@pytest.mark.asyncio
async def test_collect_posts_with_fallback_uses_stale_cache_on_api_error() -> None:
    stale_post = _post(
        subreddit="r/python",
        created_utc=time.time() - (48 * 3600),
    )

    async def _cache_get(_subreddit: str) -> list[RedditPost]:
        return [stale_post]

    async def _cache_set(_subreddit: str, _posts) -> None:
        return None

    async def _load_empty(_subreddits, _limit: int):
        return {}

    async def _fetch(_subreddit: str, _limit: int):
        raise RuntimeError("rate limit exceeded")

    result = await collect_posts_with_fallback(
        runtime_input=DataCollectionRuntimeInput(
            communities=["r/python"],
            limit_per_subreddit=5,
            cache_stale_hours=12,
            stale_fallback_enabled=True,
        ),
        deps=DataCollectionRuntimeDeps(
            cache_get=_cache_get,
            cache_set=_cache_set,
            load_hot_posts=_load_empty,
            load_cold_posts=_load_empty,
            fetch_subreddit_posts=_fetch,
            logger=logging.getLogger("test.data_collection_runtime"),
        ),
    )

    assert result.api_calls == 0
    assert result.stale_cache_subreddits == {"r/python"}
    assert result.stale_cache_fallback_subreddits == {"r/python"}
    assert result.posts_by_subreddit["r/python"][0].id == "p1"
    assert result.api_failures[0]["reason"] == "rate_limit"
