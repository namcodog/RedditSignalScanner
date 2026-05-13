from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.posts_storage import PostRaw
from app.services.crawl.incremental_cold_storage_service import (
    ColdStorageUpsertDeps,
    ColdStorageUpsertInput,
    upsert_post_to_cold_storage,
)
from app.services.crawl.incremental_crawler import (
    _posts_raw_has_community_run_id,
    _posts_raw_has_crawl_run_id,
    _unix_to_datetime,
)
from app.services.infrastructure.reddit_client import RedditPost


class TestIncrementalColdStorageService:
    @pytest_asyncio.fixture
    async def db_session(self):
        async with SessionFactory() as db:
            yield db

    @pytest_asyncio.fixture(autouse=True)
    async def _reset_tables(self, db_session) -> None:
        await db_session.execute(
            text(
                "TRUNCATE TABLE community_cache, community_pool, posts_raw, posts_hot, crawler_runs RESTART IDENTITY CASCADE"
            )
        )
        await db_session.commit()

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

    async def _ensure_pool(self, db_session) -> None:
        db_session.add(
            CommunityPool(
                name="r/test",
                tier="medium",
                categories={"topic": ["test"]},
                description_keywords={"test": 1},
                daily_posts=10,
                priority="medium",
                quality_score=Decimal("0.50"),
            )
        )
        await db_session.commit()

    def _ensure_author_dep(self, db_session):
        async def _ensure(author_id: str, author_name: str | None) -> None:
            await db_session.execute(
                text(
                    """
                    INSERT INTO authors (author_id, author_name)
                    VALUES (:author_id, :author_name)
                    ON CONFLICT (author_id) DO UPDATE
                    SET author_name = EXCLUDED.author_name
                    """
                ),
                {"author_id": author_id, "author_name": author_name},
            )
            await db_session.flush()

        return _ensure

    @pytest.mark.asyncio
    async def test_cold_storage_service_includes_run_id_metadata(self, db_session) -> None:
        await self._ensure_pool(db_session)
        run_id = str(uuid.uuid4())
        community_run_id = str(uuid.uuid4())
        post = self._mock_post()

        result = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name="r/test",
                post=post,
                source_track="incremental",
                crawl_run_id=run_id,
                community_run_id=community_run_id,
                duplicate_mode="allow",
                spam_categories={},
                crawler_run_row_ensured=False,
            ),
            deps=ColdStorageUpsertDeps(
                db=db_session,
                ensure_author=self._ensure_author_dep(db_session),
                find_content_duplicate=AsyncMock(return_value=None),
                unix_to_datetime=_unix_to_datetime,
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
            ),
        )
        await db_session.commit()

        assert result.is_new is True
        assert result.is_updated is False
        assert result.crawler_run_row_ensured is True

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

    @pytest.mark.asyncio
    async def test_cold_storage_service_drops_content_duplicate_when_configured(self, db_session) -> None:
        await self._ensure_pool(db_session)
        post = self._mock_post()

        result = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name="r/test",
                post=post,
                source_track="incremental",
                crawl_run_id=None,
                community_run_id=None,
                duplicate_mode="drop",
                spam_categories={},
                crawler_run_row_ensured=False,
            ),
            deps=ColdStorageUpsertDeps(
                db=db_session,
                ensure_author=self._ensure_author_dep(db_session),
                find_content_duplicate=AsyncMock(return_value="existing-post"),
                unix_to_datetime=_unix_to_datetime,
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
            ),
        )

        count = (
            await db_session.execute(
                select(PostRaw).where(
                    PostRaw.source == "reddit",
                    PostRaw.source_post_id == post.id,
                )
            )
        ).scalars().all()

        assert result.is_new is False
        assert result.is_updated is False
        assert count == []

    @pytest.mark.asyncio
    async def test_cold_storage_service_creates_new_version_on_score_change(self, db_session) -> None:
        await self._ensure_pool(db_session)
        post_id = str(uuid.uuid4())[:8]
        initial_post = self._mock_post(post_id=post_id)
        initial_post.score = 3
        updated_post = self._mock_post(post_id=post_id)
        updated_post.score = 10

        first = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name="r/test",
                post=initial_post,
                source_track="incremental",
                crawl_run_id=None,
                community_run_id=None,
                duplicate_mode="allow",
                spam_categories={},
                crawler_run_row_ensured=False,
            ),
            deps=ColdStorageUpsertDeps(
                db=db_session,
                ensure_author=self._ensure_author_dep(db_session),
                find_content_duplicate=AsyncMock(return_value=None),
                unix_to_datetime=_unix_to_datetime,
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
            ),
        )

        second = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name="r/test",
                post=updated_post,
                source_track="incremental",
                crawl_run_id=None,
                community_run_id=None,
                duplicate_mode="allow",
                spam_categories={},
                crawler_run_row_ensured=first.crawler_run_row_ensured,
            ),
            deps=ColdStorageUpsertDeps(
                db=db_session,
                ensure_author=self._ensure_author_dep(db_session),
                find_content_duplicate=AsyncMock(return_value=None),
                unix_to_datetime=_unix_to_datetime,
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
            ),
        )
        await db_session.commit()
        db_session.expire_all()

        versions = (
            await db_session.execute(
                select(PostRaw)
                .where(PostRaw.source == "reddit", PostRaw.source_post_id == post_id)
                .order_by(PostRaw.version.asc())
            )
        ).scalars().all()

        assert first.is_new is True
        assert second.is_updated is True
        assert len(versions) == 2
        assert versions[0].is_current is False
        assert versions[1].is_current is True
        assert versions[1].score == 10

    @pytest.mark.asyncio
    async def test_cold_storage_service_refreshes_fetched_at_for_unchanged_post(
        self,
        db_session,
    ) -> None:
        await self._ensure_pool(db_session)
        post_id = str(uuid.uuid4())[:8]
        post = self._mock_post(post_id=post_id)
        first = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name="r/test",
                post=post,
                source_track="incremental",
                crawl_run_id=None,
                community_run_id=None,
                duplicate_mode="allow",
                spam_categories={},
                crawler_run_row_ensured=False,
            ),
            deps=ColdStorageUpsertDeps(
                db=db_session,
                ensure_author=self._ensure_author_dep(db_session),
                find_content_duplicate=AsyncMock(return_value=None),
                unix_to_datetime=_unix_to_datetime,
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
            ),
        )
        await db_session.commit()
        db_session.expire_all()

        before = (
            await db_session.execute(
                select(PostRaw).where(
                    PostRaw.source == "reddit",
                    PostRaw.source_post_id == post_id,
                )
            )
        ).scalar_one()
        before_fetched_at = before.fetched_at

        second = await upsert_post_to_cold_storage(
            write_input=ColdStorageUpsertInput(
                community_name="r/test",
                post=self._mock_post(post_id=post_id),
                source_track="incremental",
                crawl_run_id=None,
                community_run_id=None,
                duplicate_mode="allow",
                spam_categories={},
                crawler_run_row_ensured=first.crawler_run_row_ensured,
            ),
            deps=ColdStorageUpsertDeps(
                db=db_session,
                ensure_author=self._ensure_author_dep(db_session),
                find_content_duplicate=AsyncMock(return_value=None),
                unix_to_datetime=_unix_to_datetime,
                posts_raw_has_crawl_run_id=_posts_raw_has_crawl_run_id,
                posts_raw_has_community_run_id=_posts_raw_has_community_run_id,
            ),
        )
        await db_session.commit()
        db_session.expire_all()

        versions = (
            await db_session.execute(
                select(PostRaw)
                .where(PostRaw.source == "reddit", PostRaw.source_post_id == post_id)
                .order_by(PostRaw.version.asc())
            )
        ).scalars().all()

        assert second.is_new is False
        assert second.is_updated is False
        assert len(versions) == 1
        assert versions[0].is_current is True
        assert versions[0].fetched_at >= before_fetched_at
