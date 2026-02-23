from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.posts_storage import PostRaw
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditPost


class TestIncrementalCrawlerRunId:
    @pytest_asyncio.fixture
    async def db_session(self):
        async with SessionFactory() as db:
            yield db

    def _mock_post(self, post_id: str | None = None) -> RedditPost:
        pid = post_id or str(uuid.uuid4())[:8]
        post = MagicMock(spec=RedditPost)
        post.id = pid
        post.title = "Test Post"
        post.selftext = "Body of Test Post"
        post.author = "test_author"
        post.score = 1
        post.num_comments = 0
        post.created_utc = datetime.now(timezone.utc).timestamp()
        post.subreddit = "test"
        post.url = f"https://reddit.com/r/test/comments/{pid}"
        post.permalink = f"/r/test/comments/{pid}"
        post.upvote_ratio = 0.95
        return post

    @pytest.mark.asyncio
    async def test_cold_storage_metadata_includes_run_id(self, db_session) -> None:
        run_id = str(uuid.uuid4())
        community_run_id = str(uuid.uuid4())
        crawler = IncrementalCrawler(
            db=db_session,
            reddit_client=AsyncMock(),
            hot_cache_ttl_hours=24,
            crawl_run_id=run_id,
            community_run_id=community_run_id,
        )
        post = self._mock_post()

        await crawler._upsert_to_cold_storage("r/test", post)
        await db_session.commit()

        stored = (
            await db_session.execute(
                select(PostRaw.extra_data).where(
                    PostRaw.source == "reddit",
                    PostRaw.source_post_id == post.id,
                )
            )
        ).scalar_one()
        metadata = json.loads(stored) if isinstance(stored, str) else stored
        assert metadata["run_id"] == run_id
        assert metadata["community_run_id"] == community_run_id

        # If schema supports it, crawl_run_id should be persisted too (FK-safe via crawler_runs).
        row = await db_session.execute(
            text(
                """
                SELECT crawl_run_id, community_run_id
                FROM posts_raw
                WHERE source='reddit' AND source_post_id=:pid
                ORDER BY version DESC
                LIMIT 1
                """
            ),
            {"pid": post.id},
        )
        crawl_run_id, stored_community_run_id = row.one()
        assert str(crawl_run_id) == run_id
        assert str(stored_community_run_id) == community_run_id
