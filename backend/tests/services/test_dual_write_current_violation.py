from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_dual_write_skips_current_unique_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc).timestamp()

    async def fake_upsert(  # noqa: ARG001
        self: IncrementalCrawler, community_name: str, post: RedditPost
    ) -> tuple[bool, bool]:
        raise IntegrityError(
            "stmt",
            {},
            Exception(
                'duplicate key value violates unique constraint "ux_posts_raw_current"'
            ),
        )

    async with SessionFactory() as session:
        crawler = IncrementalCrawler(
            db=session,
            reddit_client=None,
            crawl_run_id="run",
            community_run_id="cid",
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        monkeypatch.setattr(
            IncrementalCrawler, "_upsert_to_cold_storage", fake_upsert
        )
        monkeypatch.setattr(IncrementalCrawler, "_upsert_to_hot_cache", AsyncMock())

        post = RedditPost(
            id="p1",
            title="t",
            selftext="",
            score=1,
            num_comments=0,
            created_utc=float(now),
            subreddit="test",
            author="a",
            url="",
            permalink="",
        )
        result = await crawler._dual_write("r/test", [post])

    assert result == (0, 0, 1)
