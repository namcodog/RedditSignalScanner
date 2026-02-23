from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.tasks import crawler_task


class _DummyCacheManager:
    async def set_cached_posts(self, *_args, **_kwargs) -> None:
        return None


class _DummySession:
    async def __aenter__(self) -> "_DummySession":
        return self

    async def __aexit__(self, *_exc) -> None:
        return None

    async def commit(self) -> None:
        return None


class _DummyRedditClient:
    def __init__(self) -> None:
        self.comment_calls = 0

    async def fetch_subreddit_posts(self, *_args, **_kwargs):
        return [SimpleNamespace(id="p1")]

    async def fetch_post_comments(self, *_args, **_kwargs):
        self.comment_calls += 1
        return []

    async def fetch_subreddit_about(self, *_args, **_kwargs):
        return {}

    async def fetch_subreddit_rules(self, *_args, **_kwargs):
        return ""


@pytest.mark.asyncio
async def test_comments_preview_disabled_skips_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_upsert(*_args, **_kwargs) -> None:
        return None

    async def _noop_snapshot(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(crawler_task, "upsert_community_cache", _noop_upsert)
    monkeypatch.setattr(crawler_task, "persist_subreddit_snapshot", _noop_snapshot)
    monkeypatch.setattr(crawler_task, "SessionFactory", lambda: _DummySession())

    settings = Settings(incremental_comments_preview_enabled=False, enable_comments_sync=True)
    reddit_client = _DummyRedditClient()

    await crawler_task._crawl_single(
        "r/test_preview_off",
        settings=settings,
        cache_manager=_DummyCacheManager(),
        reddit_client=reddit_client,
        post_limit=10,
    )

    assert reddit_client.comment_calls == 0


@pytest.mark.asyncio
async def test_comments_preview_enabled_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_upsert(*_args, **_kwargs) -> None:
        return None

    async def _noop_snapshot(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(crawler_task, "upsert_community_cache", _noop_upsert)
    monkeypatch.setattr(crawler_task, "persist_subreddit_snapshot", _noop_snapshot)
    monkeypatch.setattr(crawler_task, "SessionFactory", lambda: _DummySession())

    settings = Settings(incremental_comments_preview_enabled=True, enable_comments_sync=True)
    reddit_client = _DummyRedditClient()

    await crawler_task._crawl_single(
        "r/test_preview_on",
        settings=settings,
        cache_manager=_DummyCacheManager(),
        reddit_client=reddit_client,
        post_limit=10,
    )

    assert reddit_client.comment_calls == 1
