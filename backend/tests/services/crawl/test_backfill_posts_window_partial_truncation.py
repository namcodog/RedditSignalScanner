from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.infrastructure.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_backfill_posts_window_truncated_marks_partial_and_returns_cursor_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now
    community_name = f"r/test_backfill_partial_{uuid.uuid4().hex[:8]}"

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            created = (since + timedelta(hours=1)).timestamp()
            post = RedditPost(
                id="p1",
                title="t",
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

    async def fake_dual_write(  # noqa: ARG001
        self: IncrementalCrawler,
        community_name: str,
        posts: list[RedditPost],
        trigger_comments_fetch: bool = False,
    ) -> tuple[int, int, int]:
        return (0, 0, 0)

    monkeypatch.setattr(IncrementalCrawler, "_dual_write", fake_dual_write)

    async with SessionFactory() as session:
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
        cache_row = CommunityCache(
            community_name=community_name,
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
            community_name,
            since=since,
            until=until,
            max_posts=1,
            sort="new",
        )

    assert result["status"] == "partial"
    assert result["reason"] == "cursor_remaining"
    assert result["cursor_after"] == "t3_next"
    assert result["pages_processed"] == 1

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT backfill_cursor
                FROM community_cache
                WHERE community_name = :name
                """
            ),
            {"name": community_name},
        )
        cursor_after = row.scalar_one_or_none()
        assert cursor_after == "t3_next"
