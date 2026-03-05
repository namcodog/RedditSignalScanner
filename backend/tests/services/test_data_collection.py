from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Sequence

import fakeredis.aioredis as fakeredis
from fakeredis import FakeServer
import pytest
from sqlalchemy import delete, select
from time import perf_counter

from app.db.session import SessionFactory
from app.models.posts_storage import PostHot, PostRaw
from app.services.analysis import Community
from app.services.infrastructure.cache_manager import CacheManager, DEFAULT_CACHE_TTL_SECONDS
from app.services.crawl.data_collection import CollectionResult, DataCollectionService
from app.services.infrastructure.reddit_client import RedditPost


@dataclass
class StubRedditClient:
    post_count: int
    delay: float = 0.0
    fail_subreddits: set[str] = field(default_factory=set)

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
        if subreddit in self.fail_subreddits:
            raise RuntimeError(f"rate limit for {subreddit}")
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


class FailingCache(CacheManager):
    def __init__(self) -> None:
        self.cache_ttl = DEFAULT_CACHE_TTL_SECONDS
        self.namespace = "reddit:posts"

    async def get_cached_posts(self, subreddit: str, *, max_age_hours: int = 24):  # type: ignore[override]
        raise RuntimeError("cache unavailable")

    async def set_cached_posts(self, subreddit: str, posts: Sequence[RedditPost]) -> None:  # type: ignore[override]
        # Pretend write succeeded to keep flow simple
        return None


@pytest.mark.asyncio
async def test_collect_posts_prefers_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_COLLECTION_CACHE_STALE_HOURS", "999999")
    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=1)
    service = _service(redis_client, stub_reddit)

    cached_post = RedditPost(
        id="cached",
        title="Cached",
        selftext="cached",
        score=15,
        num_comments=3,
        created_utc=1700000000.0,
        subreddit="r/python",
        author="cache",
        url="https://reddit.com/python/cached",
        permalink="/r/python/comments/cached",
    )
    cache = CacheManager(redis_client)
    await cache.set_cached_posts("r/python", [cached_post])

    communities = [_community("python"), _community("golang")]
    result = await service.collect_posts(communities)

    assert isinstance(result, CollectionResult)
    assert result.cache_hits == 1
    assert result.api_calls == 1
    assert result.cached_subreddits == {"r/python"}
    assert "r/python" in result.posts_by_subreddit
    assert "r/golang" in result.posts_by_subreddit


@pytest.mark.asyncio
async def test_collect_posts_updates_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_COLLECTION_CACHE_STALE_HOURS", "999999")
    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=1)
    service = _service(redis_client, stub_reddit)

    communities: Sequence[Community] = [_community("python"), _community("golang")]
    first = await service.collect_posts(communities)
    assert first.api_calls == 2
    assert stub_reddit.calls == ["python", "golang"]

    second = await service.collect_posts(communities)
    assert second.api_calls == 0
    assert second.cache_hits == 2
    assert second.cached_subreddits == {"r/python", "r/golang"}
    assert sorted(stub_reddit.calls) == ["golang", "python"]


@pytest.mark.asyncio
async def test_collect_posts_runs_fetches_concurrently() -> None:
    redis_client = fakeredis.FakeRedis(server=FakeServer())
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


@pytest.mark.asyncio
async def test_collect_posts_uses_hot_storage_before_api() -> None:
    """当 Redis 失效但热存储命中时，应避免调用 Reddit API。"""
    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=2)
    service = _service(redis_client, stub_reddit)

    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        hot_post = PostHot(
            source="reddit",
            source_post_id="hot-db-test",
            author_id="hot_author",
            author_name="hot_author",
            created_at=now - timedelta(hours=2),
            cached_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=12),
            title="Hot layer post",
            body="from hot storage",
            subreddit="r/python",
            score=42,
            num_comments=7,
        )
        session.add(hot_post)
        await session.commit()
        await session.refresh(hot_post)

    try:
        result = await service.collect_posts([_community("python")], limit_per_subreddit=1)

        assert result.api_calls == 0
        assert result.cache_hits == 1
        assert result.cached_subreddits == {"r/python"}
        assert stub_reddit.calls == []
        assert result.posts_by_subreddit["r/python"][0].id == "hot-db-test"
        assert result.posts_by_subreddit["r/python"][0].author == "hot_author"

        cached_posts = await CacheManager(redis_client).get_cached_posts("r/python")
        assert cached_posts and cached_posts[0].id == "hot-db-test"
        assert cached_posts[0].author == "hot_author"
    finally:
        async with SessionFactory() as cleanup:
            await cleanup.execute(delete(PostHot).where(PostHot.id == hot_post.id))
            await cleanup.commit()


@pytest.mark.asyncio
async def test_collect_posts_falls_back_to_cold_storage() -> None:
    """当热存储没有数据时，应查询冷存储并仍然避免 API 调用。"""
    from app.models.community_pool import CommunityPool

    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=2)
    service = _service(redis_client, stub_reddit)

    now = datetime.now(timezone.utc)
    created_community = False
    community_id: int | None = None
    async with SessionFactory() as session:
        result = await session.execute(select(CommunityPool).where(CommunityPool.name == "r/rust"))
        community = result.scalar_one_or_none()
        if community is None:
            community = CommunityPool(
                name="r/rust",
                tier="core",
                categories={"source": "test"},
                description_keywords={"keywords": ["rust"]},
                daily_posts=10,
                avg_comment_length=50,
                quality_score=0.5,
                priority="medium",
                is_active=True,
                is_blacklisted=False,
            )
            session.add(community)
            await session.flush()
            created_community = True
        community_id = int(community.id)

        cold_post = PostRaw(
            source="reddit",
            source_post_id="cold-db-test",
            version=3,
            author_name="cold_author",
            created_at=now - timedelta(days=7),
            fetched_at=now - timedelta(days=6, hours=12),
            valid_from=now - timedelta(days=7),
            is_current=True,
            title="Cold layer post",
            body="from cold storage",
            subreddit="r/rust",
            community_id=community_id,
            score=33,
            num_comments=4,
        )
        session.add(cold_post)
        await session.commit()
        await session.refresh(cold_post)

    try:
        result = await service.collect_posts([_community("rust")], limit_per_subreddit=1)

        assert result.api_calls == 0
        assert result.cache_hits == 1
        assert result.cached_subreddits == {"r/rust"}
        assert stub_reddit.calls == []
        assert result.posts_by_subreddit["r/rust"][0].id == "cold-db-test"
        assert result.posts_by_subreddit["r/rust"][0].author == "cold_author"

        cached_posts = await CacheManager(redis_client).get_cached_posts("r/rust")
        assert cached_posts and cached_posts[0].id == "cold-db-test"
        assert cached_posts[0].author == "cold_author"
    finally:
        async with SessionFactory() as cleanup:
            await cleanup.execute(delete(PostRaw).where(PostRaw.source_post_id == "cold-db-test"))
            if created_community and community_id is not None:
                await cleanup.execute(delete(CommunityPool).where(CommunityPool.id == community_id))
            await cleanup.commit()


@pytest.mark.asyncio
async def test_collect_posts_normalizes_subreddit_names_for_db_lookup() -> None:
    """社区名大小写/是否带 r/ 不应导致错过冷库数据而误打 Reddit API。"""
    from app.models.community_pool import CommunityPool

    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=1)
    service = _service(redis_client, stub_reddit)

    now = datetime.now(timezone.utc)
    community_id: int | None = None
    created_community = False
    async with SessionFactory() as session:
        result = await session.execute(select(CommunityPool).where(CommunityPool.name == "r/ppc"))
        community = result.scalar_one_or_none()
        if community is None:
            community = CommunityPool(
                name="r/ppc",
                tier="core",
                categories={"source": "test"},
                description_keywords={"keywords": ["ppc"]},
                daily_posts=10,
                avg_comment_length=50,
                quality_score=0.5,
                priority="medium",
                is_active=True,
                is_blacklisted=False,
            )
            session.add(community)
            await session.flush()
            created_community = True
        community_id = int(community.id)

        cold_post = PostRaw(
            source="reddit",
            source_post_id="ppc-cold-db-test",
            version=1,
            author_name="ppc_author",
            created_at=now - timedelta(days=3),
            fetched_at=now - timedelta(days=2),
            valid_from=now - timedelta(days=3),
            is_current=True,
            title="PPC strategy discussion",
            body="Talking about ROAS and CPC tuning.",
            subreddit="r/ppc",
            community_id=community_id,
            score=10,
            num_comments=2,
        )
        session.add(cold_post)
        await session.commit()
        await session.refresh(cold_post)

    try:
        result = await service.collect_posts([_community("r/PPC")], limit_per_subreddit=1)

        assert result.api_calls == 0
        assert stub_reddit.calls == []
        assert "r/ppc" in result.posts_by_subreddit
        assert result.posts_by_subreddit["r/ppc"][0].id == "ppc-cold-db-test"
    finally:
        async with SessionFactory() as cleanup:
            await cleanup.execute(delete(PostRaw).where(PostRaw.source_post_id == "ppc-cold-db-test"))
            if created_community and community_id is not None:
                await cleanup.execute(delete(CommunityPool).where(CommunityPool.id == community_id))
            await cleanup.commit()


@pytest.mark.asyncio
async def test_collect_posts_handles_cache_failures() -> None:
    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        hot_post = PostHot(
            source="reddit",
            source_post_id="cache-fallback",
            author_id="cache_author",
            author_name="cache_author",
            created_at=now - timedelta(hours=2),
            cached_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=6),
            title="Cache fallback",
            body="from hot storage",
            subreddit="r/python",
            score=30,
            num_comments=5,
        )
        session.add(hot_post)
        await session.commit()
        await session.refresh(hot_post)

    try:
        stub_reddit = StubRedditClient(post_count=0)
        cache = FailingCache()
        service = DataCollectionService(stub_reddit, cache)

        result = await service.collect_posts([_community("python")], limit_per_subreddit=1)
        assert result.api_calls == 0
        assert result.total_posts == 1
        assert result.posts_by_subreddit["r/python"][0].id == "cache-fallback"
    finally:
        async with SessionFactory() as cleanup:
            await cleanup.execute(delete(PostHot).where(PostHot.source_post_id == "cache-fallback"))
            await cleanup.commit()


@pytest.mark.asyncio
async def test_collect_posts_skips_stale_cache_and_uses_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_COLLECTION_CACHE_STALE_HOURS", "1")

    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=1)
    service = _service(redis_client, stub_reddit)

    stale_at = datetime.now(timezone.utc) - timedelta(hours=2)
    cached_post = RedditPost(
        id="cached-stale",
        title="Cached",
        selftext="cached",
        score=15,
        num_comments=3,
        created_utc=stale_at.timestamp(),
        subreddit="r/python",
        author="cache",
        url="https://reddit.com/python/cached",
        permalink="/r/python/comments/cached",
    )
    cache = CacheManager(redis_client)
    await cache.set_cached_posts("r/python", [cached_post])

    result = await service.collect_posts([_community("python")])

    assert result.cache_hits == 0
    assert result.api_calls == 1
    assert result.cached_subreddits == set()
    assert result.stale_cache_subreddits == {"r/python"}
    assert result.stale_cache_fallback_subreddits == set()
    assert stub_reddit.calls == ["python"]


@pytest.mark.asyncio
async def test_collect_posts_uses_stale_cache_when_api_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_COLLECTION_CACHE_STALE_HOURS", "1")
    monkeypatch.setenv("DATA_COLLECTION_STALE_FALLBACK_ENABLED", "1")

    redis_client = fakeredis.FakeRedis(server=FakeServer())
    stub_reddit = StubRedditClient(post_count=1, fail_subreddits={"python"})
    service = _service(redis_client, stub_reddit)

    stale_at = datetime.now(timezone.utc) - timedelta(hours=4)
    cached_post = RedditPost(
        id="cached-stale-fallback",
        title="Cached",
        selftext="cached",
        score=15,
        num_comments=3,
        created_utc=stale_at.timestamp(),
        subreddit="r/python",
        author="cache",
        url="https://reddit.com/python/cached",
        permalink="/r/python/comments/cached",
    )
    cache = CacheManager(redis_client)
    await cache.set_cached_posts("r/python", [cached_post])

    result = await service.collect_posts([_community("python")])

    assert result.api_calls == 0
    assert result.cache_hits == 0
    assert result.cached_subreddits == set()
    assert result.stale_cache_subreddits == {"r/python"}
    assert result.stale_cache_fallback_subreddits == {"r/python"}
    assert result.posts_by_subreddit["r/python"][0].id == "cached-stale-fallback"
    assert result.api_failures
