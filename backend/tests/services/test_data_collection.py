from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Sequence

import fakeredis
import pytest
from time import perf_counter

from app.services.analysis import Community
from app.services.cache_manager import CacheManager
from app.services.data_collection import CollectionResult, DataCollectionService
from app.services.reddit_client import RedditPost


@dataclass
class StubRedditClient:
    post_count: int
    delay: float = 0.0

    def __post_init__(self) -> None:
        self.calls: List[str] = []
        self.max_concurrency: int = 0
        self._inflight: int = 0

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        *,
        limit: int = 100,
    ) -> List[RedditPost]:
        self._inflight += 1
        try:
            self.max_concurrency = max(self.max_concurrency, self._inflight)
            if self.delay:
                await asyncio.sleep(self.delay)
        finally:
            self._inflight -= 1
        self.calls.append(subreddit)
        return [
            RedditPost(
                id=f"{subreddit}-{index}",
                title=f"{subreddit} post {index}",
                selftext="Body",
                score=10 + index,
                num_comments=2,
                created_utc=1700000000.0,
                subreddit=subreddit,
                author="tester",
                url=f"https://reddit.com/{subreddit}/{index}",
                permalink=f"/r/{subreddit}/comments/{index}",
            )
            for index in range(self.post_count)
        ]


def _community(name: str) -> Community:
    return Community(
        name=name,
        categories=("tech",),
        description_keywords=("ai",),
        daily_posts=100,
        avg_comment_length=80,
        relevance_score=0.9,
    )


def _service(redis_client: fakeredis.FakeRedis, reddit_client: StubRedditClient) -> DataCollectionService:
    cache = CacheManager(redis_client)
    return DataCollectionService(reddit_client, cache)


@pytest.mark.asyncio
async def test_collect_posts_prefers_cache() -> None:
    redis_client = fakeredis.FakeRedis()
    stub_reddit = StubRedditClient(post_count=1)
    service = _service(redis_client, stub_reddit)

    cached_post = RedditPost(
        id="cached",
        title="Cached",
        selftext="cached",
        score=15,
        num_comments=3,
        created_utc=1700000000.0,
        subreddit="python",
        author="cache",
        url="https://reddit.com/python/cached",
        permalink="/r/python/comments/cached",
    )
    cache = CacheManager(redis_client)
    cache.set_cached_posts("python", [cached_post])

    communities = [_community("python"), _community("golang")]
    result = await service.collect_posts(communities)

    assert isinstance(result, CollectionResult)
    assert result.cache_hits == 1
    assert result.api_calls == 1
    assert result.cached_subreddits == {"python"}
    assert "python" in result.posts_by_subreddit
    assert "golang" in result.posts_by_subreddit


@pytest.mark.asyncio
async def test_collect_posts_updates_cache() -> None:
    redis_client = fakeredis.FakeRedis()
    stub_reddit = StubRedditClient(post_count=1)
    service = _service(redis_client, stub_reddit)

    communities: Sequence[Community] = [_community("python"), _community("golang")]
    first = await service.collect_posts(communities)
    assert first.api_calls == 2
    assert stub_reddit.calls == ["python", "golang"]

    second = await service.collect_posts(communities)
    assert second.api_calls == 0
    assert second.cache_hits == 2
    assert second.cached_subreddits == {"python", "golang"}
    assert sorted(stub_reddit.calls) == ["golang", "python"]


@pytest.mark.asyncio
async def test_collect_posts_runs_fetches_concurrently() -> None:
    redis_client = fakeredis.FakeRedis()
    stub_reddit = StubRedditClient(post_count=1, delay=0.05)
    service = _service(redis_client, stub_reddit)

    communities: Sequence[Community] = [
        _community("python"),
        _community("golang"),
        _community("rust"),
    ]

    start = perf_counter()
    result = await service.collect_posts(communities)
    elapsed = perf_counter() - start

    assert result.api_calls == 3
    assert stub_reddit.max_concurrency >= 2
    # Sequential fetching would take ~0.15s (3 * 0.05). Concurrency keeps it below the threshold.
    assert elapsed < 0.14
