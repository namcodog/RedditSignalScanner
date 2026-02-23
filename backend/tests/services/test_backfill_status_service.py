from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.community_cache_service import (
    mark_backfill_running,
    update_backfill_status,
)


@pytest.mark.asyncio
async def test_mark_backfill_running_and_update_status() -> None:
    now = datetime.now(timezone.utc)
    async with SessionFactory() as session:
        session.add(
            CommunityCache(
                community_name="r/backfill_status",
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.50"),
            )
        )
        await session.commit()

    async with SessionFactory() as session:
        await mark_backfill_running("r/backfill_status", session=session)
        await update_backfill_status(
            "r/backfill_status",
            status="DONE_12M",
            coverage_months=12,
            sample_posts=123,
            sample_comments=456,
            backfill_capped=False,
            cursor_after=None,
            cursor_created_at=None,
            session=session,
        )
        await session.commit()

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT backfill_status, coverage_months, sample_posts, sample_comments, backfill_capped
                FROM community_cache
                WHERE community_name = :name
                """
            ),
            {"name": "r/backfill_status"},
        )
        status, months, posts, comments, capped = row.one()
        assert status == "DONE_12M"
        assert months == 12
        assert posts == 123
        assert comments == 456
        assert capped is False


@pytest.mark.asyncio
async def test_update_backfill_status_keeps_cursor_when_none() -> None:
    now = datetime.now(timezone.utc)
    cursor_time = now - timedelta(days=1)
    async with SessionFactory() as session:
        session.add(
            CommunityCache(
                community_name="r/backfill_cursor_keep",
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal("0.50"),
                backfill_cursor="t3_old_cursor",
                backfill_cursor_created_at=cursor_time,
            )
        )
        await session.commit()

    async with SessionFactory() as session:
        await update_backfill_status(
            "r/backfill_cursor_keep",
            status="ERROR",
            coverage_months=3,
            sample_posts=10,
            sample_comments=20,
            backfill_capped=True,
            cursor_after=None,
            cursor_created_at=None,
            session=session,
        )
        await session.commit()

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT backfill_cursor, backfill_cursor_created_at
                FROM community_cache
                WHERE community_name = :name
                """
            ),
            {"name": "r/backfill_cursor_keep"},
        )
        cursor, created_at = row.one()
        assert cursor == "t3_old_cursor"
        assert created_at == cursor_time
