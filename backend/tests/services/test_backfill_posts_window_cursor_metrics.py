from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_backfill_posts_window_sets_cursor_created_before_after_from_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now
    newer = (since + timedelta(hours=5)).timestamp()
    older = (since + timedelta(hours=1)).timestamp()

    class DummyReddit:
        async def fetch_subreddit_posts(
            self, *_: Any, **__: Any
        ) -> tuple[list[RedditPost], str | None]:
            return (
                [
                    RedditPost(
                        id="p_new",
                        title="new",
                        selftext="",
                        score=1,
                        num_comments=0,
                        created_utc=float(newer),
                        subreddit="test",
                        author="a",
                        url="",
                        permalink="",
                    ),
                    RedditPost(
                        id="p_old",
                        title="old",
                        selftext="",
                        score=1,
                        num_comments=0,
                        created_utc=float(older),
                        subreddit="test",
                        author="a",
                        url="",
                        permalink="",
                    ),
                ],
                None,
            )

    async def fake_dual_write(  # noqa: ARG001
        self: IncrementalCrawler,
        community_name: str,
        posts: list[RedditPost],
        trigger_comments_fetch: bool = False,
    ) -> tuple[int, int, int]:
        return (0, 0, 0)

    monkeypatch.setattr(IncrementalCrawler, "_dual_write", fake_dual_write)

    async with SessionFactory() as session:
        cache_row = CommunityCache(
            community_name="r/test_backfill_cursor_metrics",
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
            "r/test_backfill_cursor_metrics",
            since=since,
            until=until,
            max_posts=10,
            sort="new",
        )

    assert result["cursor_created_before"] is not None
    assert result["cursor_created_after"] is not None
    before = datetime.fromisoformat(result["cursor_created_before"])
    after = datetime.fromisoformat(result["cursor_created_after"])
    assert after < before
