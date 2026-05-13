from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community import community_cache_service


async def _seed_cache_community(
    session, *, community_name: str, now: datetime, **cache_overrides
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
            **cache_overrides,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_mark_backfill_running_and_update_status() -> None:
    now = datetime.now(timezone.utc)
    community_name = f"r/backfill_status_{uuid.uuid4().hex[:8]}"
    async with SessionFactory() as session:
        await _seed_cache_community(session, community_name=community_name, now=now)

    async with SessionFactory() as session:
        await community_cache_service.mark_backfill_running(
            community_name, session=session
        )
        await community_cache_service.update_backfill_status(
            community_name,
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
            {"name": community_name},
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
    community_name = f"r/backfill_cursor_keep_{uuid.uuid4().hex[:8]}"
    async with SessionFactory() as session:
        await _seed_cache_community(
            session,
            community_name=community_name,
            now=now,
            backfill_cursor="t3_old_cursor",
            backfill_cursor_created_at=cursor_time,
        )

    async with SessionFactory() as session:
        await community_cache_service.update_backfill_status(
            community_name,
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
            {"name": community_name},
        )
        cursor, created_at = row.one()
        assert cursor == "t3_old_cursor"
        assert created_at == cursor_time
