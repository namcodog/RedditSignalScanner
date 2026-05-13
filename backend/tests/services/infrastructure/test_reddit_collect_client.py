from __future__ import annotations

import pytest

from app.services.infrastructure.reddit_client import RedditAPIError, RedditPost
from app.services.infrastructure import reddit_collect_client as collect_mod
from app.services.infrastructure.reddit_collect_client import CollectRedditClient


pytestmark = pytest.mark.asyncio


class _PrimaryClient:
    def __init__(self, *, fail_with: RedditAPIError | None = None, skip_comments: bool = False, low_quota: bool = False) -> None:
        self.fail_with = fail_with
        self.skip_comments = skip_comments
        self.low_quota = low_quota
        self.calls: list[tuple[str, str]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def close(self) -> None:
        return None

    def should_skip_comment_fetch(self) -> bool:
        return self.skip_comments

    def is_low_quota(self) -> bool:
        return self.low_quota

    async def search_subreddit_page(self, subreddit: str, query: str, **kwargs):
        self.calls.append(("search", subreddit))
        if self.fail_with is not None:
            raise self.fail_with
        return ([], None)

    async def fetch_subreddit_posts(self, subreddit: str, **kwargs):
        self.calls.append(("listing", subreddit))
        if self.fail_with is not None:
            raise self.fail_with
        return ([], None)

    async def fetch_post_comments(self, post_id: str, **kwargs):
        self.calls.append(("comments", post_id))
        if self.fail_with is not None:
            raise self.fail_with
        return []


class _FallbackClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def close(self) -> None:
        return None

    async def search_subreddit_page(self, subreddit: str, query: str, **kwargs):
        self.calls.append(("search", subreddit))
        return ([RedditPost(id="p1", title="t", selftext="", score=1, num_comments=1, created_utc=1.0, subreddit=subreddit, author="a", url="u", permalink="/p1")], None)

    async def fetch_subreddit_posts(self, subreddit: str, **kwargs):
        self.calls.append(("listing", subreddit))
        return ([RedditPost(id="p1", title="t", selftext="", score=1, num_comments=1, created_utc=1.0, subreddit=subreddit, author="a", url="u", permalink="/p1")], None)

    async def fetch_post_comments(self, post_id: str, **kwargs):
        self.calls.append(("comments", post_id))
        return [{"body": "comment", "score": 1, "author": "u", "permalink": "/c1"}]


async def test_collect_reddit_client_falls_back_on_rate_limit() -> None:
    primary = _PrimaryClient(fail_with=RedditAPIError("Reddit API rate limit exceeded after 3 retries."))
    fallback = _FallbackClient()
    client = CollectRedditClient(primary=primary, fallback=fallback)

    posts, _ = await client.search_subreddit_page("OpenAI", "openai", limit=5)

    assert len(posts) == 1
    assert fallback.calls == [("search", "OpenAI")]


async def test_collect_reddit_client_uses_fallback_comments_when_primary_quota_low() -> None:
    primary = _PrimaryClient(skip_comments=True)
    fallback = _FallbackClient()
    client = CollectRedditClient(primary=primary, fallback=fallback)

    comments = await client.fetch_post_comments("post-1", limit=10)

    assert comments[0]["body"] == "comment"
    assert fallback.calls == [("comments", "post-1")]


async def test_collect_reddit_client_uses_fallback_comments_when_primary_returns_empty() -> None:
    primary = _PrimaryClient()
    fallback = _FallbackClient()
    client = CollectRedditClient(primary=primary, fallback=fallback)

    comments = await client.fetch_post_comments("post-2", limit=10)

    assert comments[0]["body"] == "comment"
    assert primary.calls == [("comments", "post-2")]
    assert fallback.calls == [("comments", "post-2")]


async def test_collect_reddit_client_keeps_reddit_api_as_primary_for_posts_when_quota_is_low() -> None:
    primary = _PrimaryClient(low_quota=True)
    fallback = _FallbackClient()
    client = CollectRedditClient(primary=primary, fallback=fallback)

    posts, _ = await client.fetch_subreddit_posts("OpenAI", limit=5)

    assert posts == []
    assert primary.calls == [("listing", "OpenAI")]
    assert fallback.calls == []
    assert client.get_collect_stats()["primary_post_requests"] == 1


async def test_collect_reddit_client_uses_fallback_for_secondary_discover_assist_when_requested() -> None:
    primary = _PrimaryClient()
    fallback = _FallbackClient()
    client = CollectRedditClient(primary=primary, fallback=fallback)

    posts, _ = await client.search_subreddit_page(
        "OpenAI",
        "openai workflow",
        limit=5,
        prefer_fallback=True,
    )

    assert len(posts) == 1
    assert primary.calls == []
    assert fallback.calls == [("search", "OpenAI")]
    assert client.get_collect_stats()["discover_assist_hits"] == 1


async def test_build_collect_reddit_client_keeps_stats_wrapper_without_sociavault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _PrimaryFactory:
        def __call__(self, *args, **kwargs):
            return _PrimaryClient()

    monkeypatch.setattr(collect_mod, "RedditAPIClient", _PrimaryFactory())
    monkeypatch.setattr(
        collect_mod,
        "settings",
        type(
            "_Settings",
            (),
            {
                "reddit_client_id": "cid",
                "reddit_client_secret": "secret",
                "reddit_user_agent": "ua",
                "sociavault_reddit_fallback_enabled": False,
                "sociavault_api_key": "",
                "sociavault_base_url": "https://api.sociavault.com/v1",
            },
        )(),
    )

    client = collect_mod.build_collect_reddit_client(
        request_timeout=20.0,
        search_timeout=12.0,
        max_concurrency=2,
        low_quota_remaining_threshold=25,
        low_quota_cooldown_seconds=20.0,
        stop_comment_fetch_below_remaining=30,
        max_consecutive_rate_limit_errors=3,
    )

    assert isinstance(client, CollectRedditClient)
    assert client.fallback is None
    assert client.get_collect_stats()["primary_post_requests"] == 0
