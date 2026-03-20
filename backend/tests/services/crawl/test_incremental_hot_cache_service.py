from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.posts_storage import PostHot
from app.services.crawl.incremental_hot_cache_service import (
    HotCacheUpsertDeps,
    HotCacheUpsertInput,
    upsert_post_to_hot_cache,
)
from app.services.crawl.incremental_crawler import _unix_to_datetime
from app.services.infrastructure.reddit_client import RedditPost


class TestIncrementalHotCacheService:
    @pytest_asyncio.fixture
    async def db_session(self):
        async with SessionFactory() as db:
            yield db

    @pytest_asyncio.fixture(autouse=True)
    async def _reset_tables(self, db_session) -> None:
        await db_session.execute(
            text("TRUNCATE TABLE posts_hot RESTART IDENTITY CASCADE")
        )
        await db_session.commit()

    def _mock_post(self, post_id: str | None = None) -> RedditPost:
        pid = post_id or str(uuid.uuid4())[:8]
        post = MagicMock(spec=RedditPost)
        post.id = pid
        post.title = "Test Hot Post"
        post.selftext = "Hot body"
        post.author = "hot_author"
        post.score = 12
        post.num_comments = 3
        post.created_utc = datetime.now(timezone.utc).timestamp()
        post.subreddit = "test"
        post.url = f"https://reddit.com/r/test/comments/{pid}"
        post.permalink = f"/r/test/comments/{pid}"
        return post

    @pytest.mark.asyncio
    async def test_hot_cache_service_persists_author_and_permalink(self, db_session) -> None:
        post = self._mock_post()

        await upsert_post_to_hot_cache(
            write_input=HotCacheUpsertInput(
                community_name="r/test",
                post=post,
                hot_cache_ttl_hours=24,
            ),
            deps=HotCacheUpsertDeps(
                db=db_session,
                ensure_author=AsyncMock(),
                unix_to_datetime=_unix_to_datetime,
            ),
        )
        await db_session.commit()

        row = (
            await db_session.execute(
                select(PostHot).where(
                    PostHot.source == "reddit",
                    PostHot.source_post_id == post.id,
                )
            )
        ).scalar_one()

        assert row.author_id == "hot_author"
        assert row.author_name == "hot_author"
        assert row.subreddit == "r/test"
        assert row.extra_data["permalink"] == post.permalink
