from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.crawl.single_crawl_workflow import (
    SingleCrawlWorkflowDeps,
    SingleCrawlWorkflowInput,
    run_single_crawl_workflow,
)


class _DummySession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> "_DummySession":
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_single_crawl_workflow_retries_after_rate_limit() -> None:
    posts = [SimpleNamespace(id="p1")]
    fetch_calls: list[int] = []
    cache_calls: list[tuple[str, int, int | None]] = []

    async def _fetch_comprehensive(*_args, **_kwargs):
        raise RuntimeError("rate limit hit")

    async def _fetch_subreddit_posts(_subreddit: str, limit: int, *_args):
        fetch_calls.append(limit)
        return posts

    async def _set_cached_posts(community: str, cached_posts, ttl_seconds: int | None) -> None:
        cache_calls.append((community, len(list(cached_posts)), ttl_seconds))

    async def _noop(*_args, **_kwargs) -> None:
        return None

    async def _fetch_about(*_args, **_kwargs):
        return {}

    async def _fetch_rules(*_args, **_kwargs):
        return ""

    result = await run_single_crawl_workflow(
        workflow_input=SingleCrawlWorkflowInput(
            community_name="r/testsub",
            post_limit=120,
            time_filter="month",
            sort="top",
            start_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            community_cache_ttl_seconds=3600,
            hot_cache_ttl_hours=24,
            comments_preview_enabled=False,
            comments_topn_limit=20,
        ),
        deps=SingleCrawlWorkflowDeps(
            normalize_subreddit_name=lambda name: name[2:],
            fetch_comprehensive_posts=_fetch_comprehensive,
            fetch_subreddit_posts=_fetch_subreddit_posts,
            is_rate_limit_error=lambda exc: "rate limit" in str(exc).lower(),
            set_cached_posts=_set_cached_posts,
            upsert_community_cache=lambda *_args, **_kwargs: _noop(),
            fetch_subreddit_about=_fetch_about,
            fetch_subreddit_rules=_fetch_rules,
            session_factory=lambda: _DummySession(),
            persist_subreddit_snapshot=_noop,
            fetch_post_comments=lambda *_args, **_kwargs: _noop(),
            persist_comments=_noop,
            rollback_with_warning=lambda *_args, **_kwargs: _noop(),
            log_debug=lambda *_args, **_kwargs: None,
        ),
    )

    assert fetch_calls == [60]
    assert cache_calls == [("r/testsub", 1, 86400)]
    assert result.payload["rate_limited"] is True
    assert result.payload["effective_post_limit"] == 60


@pytest.mark.asyncio
async def test_single_crawl_workflow_preview_comments_enabled() -> None:
    posts = [SimpleNamespace(id="p1"), SimpleNamespace(id="p2")]
    comment_calls: list[str] = []
    persisted_comment_posts: list[str] = []

    async def _fetch_subreddit_posts(*_args, **_kwargs):
        return posts

    async def _fetch_comments(post_id: str, **_kwargs):
        comment_calls.append(post_id)
        return [SimpleNamespace(id=f"c-{post_id}")]

    async def _persist_comments(_db, *, source_post_id: str, **_kwargs) -> None:
        persisted_comment_posts.append(source_post_id)

    async def _noop(*_args, **_kwargs) -> None:
        return None

    async def _fetch_about(*_args, **_kwargs):
        return {}

    async def _fetch_rules(*_args, **_kwargs):
        return ""

    result = await run_single_crawl_workflow(
        workflow_input=SingleCrawlWorkflowInput(
            community_name="r/testsub",
            post_limit=10,
            time_filter="month",
            sort="top",
            start_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            community_cache_ttl_seconds=3600,
            hot_cache_ttl_hours=None,
            comments_preview_enabled=True,
            comments_topn_limit=50,
        ),
        deps=SingleCrawlWorkflowDeps(
            normalize_subreddit_name=lambda name: name[2:],
            fetch_comprehensive_posts=lambda *_args, **_kwargs: _noop(),
            fetch_subreddit_posts=_fetch_subreddit_posts,
            is_rate_limit_error=lambda _exc: False,
            set_cached_posts=lambda *_args, **_kwargs: _noop(),
            upsert_community_cache=lambda *_args, **_kwargs: _noop(),
            fetch_subreddit_about=_fetch_about,
            fetch_subreddit_rules=_fetch_rules,
            session_factory=lambda: _DummySession(),
            persist_subreddit_snapshot=_noop,
            fetch_post_comments=_fetch_comments,
            persist_comments=_persist_comments,
            rollback_with_warning=lambda *_args, **_kwargs: _noop(),
            log_debug=lambda *_args, **_kwargs: None,
        ),
    )

    assert result.payload["posts_count"] == 2
    assert comment_calls == ["p1", "p2"]
    assert persisted_comment_posts == ["p1", "p2"]
