from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.crawl.incremental_crawler_deps_factory import (
    IncrementalCrawlerDepsFactoryInput,
    build_comprehensive_crawl_workflow_deps,
    build_incremental_crawl_workflow_deps,
)


def _factory_input(**overrides):
    reddit_client = overrides.get(
        "reddit_client",
        SimpleNamespace(
            fetch_subreddit_posts=AsyncMock(return_value=[]),
            fetch_comprehensive_posts=AsyncMock(return_value=[]),
        ),
    )
    return IncrementalCrawlerDepsFactoryInput(
        reddit_client=reddit_client,
        get_watermark=overrides.get("get_watermark", AsyncMock(return_value=None)),
        filter_spam_posts=overrides.get(
            "filter_spam_posts", lambda _community, posts: posts
        ),
        dual_write=overrides.get("dual_write", AsyncMock(return_value=(0, 0, 0))),
        dispatch_score_refresh=overrides.get(
            "dispatch_score_refresh", AsyncMock(return_value=None)
        ),
        update_watermark=overrides.get("update_watermark", AsyncMock(return_value=None)),
        record_failure_attempt=overrides.get(
            "record_failure_attempt", AsyncMock(return_value=None)
        ),
        record_empty_attempt=overrides.get(
            "record_empty_attempt", AsyncMock(return_value=None)
        ),
        record_crawl_metrics=overrides.get(
            "record_crawl_metrics", AsyncMock(return_value=None)
        ),
        normalize_subreddit_name=overrides.get(
            "normalize_subreddit_name", lambda value: value.removeprefix("r/")
        ),
        unix_to_datetime=overrides.get(
            "unix_to_datetime",
            lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc),
        ),
    )


@pytest.mark.asyncio
async def test_incremental_crawl_deps_factory_fetch_posts_uses_reddit_client() -> None:
    reddit_client = SimpleNamespace(
        fetch_subreddit_posts=AsyncMock(return_value=["post"]),
        fetch_comprehensive_posts=AsyncMock(return_value=[]),
    )
    deps = build_incremental_crawl_workflow_deps(
        _factory_input(reddit_client=reddit_client)
    )

    result = await deps.fetch_posts("test", 10, "day", "top")

    assert result == ["post"]
    reddit_client.fetch_subreddit_posts.assert_awaited_once_with(
        "test",
        limit=10,
        time_filter="day",
        sort="top",
    )


@pytest.mark.asyncio
async def test_comprehensive_crawl_deps_factory_wraps_watermark_update() -> None:
    update_watermark = AsyncMock()
    deps = build_comprehensive_crawl_workflow_deps(
        _factory_input(update_watermark=update_watermark)
    )

    now = datetime.now(timezone.utc)
    await deps.update_watermark("r/test", "p1", now, 10, 2, 30.0)

    update_watermark.assert_awaited_once_with(
        "r/test",
        "p1",
        now,
        total_fetched=10,
        new_valid_posts=2,
        dedup_rate=30.0,
    )


@pytest.mark.asyncio
async def test_incremental_crawl_deps_factory_requires_reddit_client() -> None:
    deps = build_incremental_crawl_workflow_deps(
        _factory_input(reddit_client=None)
    )

    with pytest.raises(ValueError, match="RedditAPIClient is required"):
        await deps.fetch_posts("test", 10, "day", "top")
