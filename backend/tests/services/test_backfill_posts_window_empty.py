from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.services.reddit_client import RedditPost
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.incremental_crawler import IncrementalCrawler


@pytest.mark.asyncio
async def test_backfill_posts_window_empty_returns_partial_when_budget_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            created = (until + timedelta(hours=1)).timestamp()
            post = RedditPost(
                id="p_future",
                title="future",
                selftext="",
                score=1,
                num_comments=0,
                created_utc=float(created),
                subreddit="test",
                author="a",
                url="",
                permalink="",
            )
            return [post], "t3_next"

    monkeypatch.setenv("BACKFILL_MAX_PAGES_PER_RUN", "1")

    async with SessionFactory() as session:
        cache_row = CommunityCache(
            community_name="r/test_backfill_empty_budget",
            last_crawled_at=now,
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.50"),
        )
        session.add(cache_row)
        await session.commit()

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="cid",
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        result = await crawler.backfill_posts_window(
            "r/test_backfill_empty_budget",
            since=since,
            until=until,
            max_posts=10,
            sort="new",
        )

    assert result["status"] == "partial"
    assert result["reason"] == "budget_remaining"
    assert result["stop_reason"] == "budget_remaining"
    assert result["metrics_schema_version"] == 2
    assert result["total_fetched"] == 0
    assert result["api_calls_total"] == 1
    assert result["items_api_returned"] == 1


@pytest.mark.asyncio
async def test_backfill_posts_window_empty_completed_when_no_more_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            return [], None

    async with SessionFactory() as session:
        cache_row = CommunityCache(
            community_name="r/test_backfill_empty_nomore",
            last_crawled_at=now,
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.50"),
        )
        session.add(cache_row)
        await session.commit()

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="cid",
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        result = await crawler.backfill_posts_window(
            "r/test_backfill_empty_nomore",
            since=since,
            until=until,
            max_posts=10,
            sort="new",
        )

    assert result["status"] == "completed"
    assert result["reason"] is None
    assert result["stop_reason"] == "no_more_pages"
    assert result["metrics_schema_version"] == 2
    assert result["total_fetched"] == 0
    assert result["api_calls_total"] == 1
    assert result["pages_processed"] == 0
