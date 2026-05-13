from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.infrastructure.reddit_client import RedditPost


async def _seed_cache_community(
    session: Any, *, community_name: str, now: datetime
) -> None:
    session.add(
        CommunityPool(
            name=community_name,
            tier="medium",
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=10,
            priority="medium",
        )
    )
    await session.flush()
    session.add(
        CommunityCache(
            community_name=community_name,
            last_crawled_at=now,
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.50"),
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_backfill_posts_window_empty_returns_partial_when_budget_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now
    community_name = f"r/test_backfill_empty_budget_{uuid.uuid4().hex[:8]}"

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
        await _seed_cache_community(session, community_name=community_name, now=now)

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="cid",
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        result = await crawler.backfill_posts_window(
            community_name,
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
    community_name = f"r/test_backfill_empty_nomore_{uuid.uuid4().hex[:8]}"

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            return [], None

    async with SessionFactory() as session:
        await _seed_cache_community(session, community_name=community_name, now=now)

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="cid",
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        result = await crawler.backfill_posts_window(
            community_name,
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
