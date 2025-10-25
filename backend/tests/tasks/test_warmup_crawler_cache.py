import asyncio
from typing import Any, List

import pytest

from app.tasks.warmup_crawler import _crawl_community
from app.services.reddit_client import RedditPost


class DummyDB:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeCacheManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def set_cached_posts(self, subreddit: str, posts: List[RedditPost]) -> None:
        self.calls.append((subreddit, len(posts)))


class FakeRedditClient:
    async def fetch_subreddit_posts(self, subreddit: str, *, limit: int = 100, time_filter: str = "week", sort: str = "top") -> List[RedditPost]:
        return [
            RedditPost(
                id="abc",
                title="Hello",
                selftext="",
                score=10,
                num_comments=2,
                created_utc=0.0,
                subreddit=subreddit,
                author="tester",
                url="http://example.com",
                permalink="/r/x/abc",
            ),
            RedditPost(
                id="def",
                title="World",
                selftext="",
                score=5,
                num_comments=1,
                created_utc=0.0,
                subreddit=subreddit,
                author="tester",
                url="http://example.com",
                permalink="/r/x/def",
            ),
        ]


class Community:
    def __init__(self, name: str) -> None:
        self.name = name


@pytest.mark.asyncio
async def test_crawl_community_stores_posts_and_commits(monkeypatch: Any) -> None:
    # Arrange
    db = DummyDB()
    cache = FakeCacheManager()
    client = FakeRedditClient()
    community = Community("artificial")

    upsert_calls: list[tuple[str, int, int]] = []

    async def fake_upsert(*, community_name: str, posts_cached: int, ttl_seconds: int, session: Any) -> None:  # type: ignore[no-redef]
        upsert_calls.append((community_name, posts_cached, ttl_seconds))

    # Patch upsert_community_cache used inside function
    import app.tasks.warmup_crawler as mod

    monkeypatch.setattr(mod, "upsert_community_cache", fake_upsert)

    # Act
    count = await _crawl_community(db, client, cache, community)  # type: ignore[arg-type]

    # Assert
    assert count == 2
    assert db.committed is True
    assert cache.calls == [("artificial", 2)]
    assert len(upsert_calls) == 1
    assert upsert_calls[0][0] == "artificial"
    assert upsert_calls[0][1] == 2
