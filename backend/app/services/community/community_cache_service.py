from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache


async def upsert_community_cache(
    community_name: str,
    *,
    posts_cached: int,
    ttl_seconds: int,
    quality_score: float | None = None,
    session: AsyncSession | None = None,
) -> None:
    """
    Create or update a CommunityCache entry with the latest crawl metadata.

    Parameters mirror the Day 13 PRD requirements where the crawler must keep
    Redis和数据库一致，确保缓存命中率监控字段最新。
    """

    if session is not None:
        await _upsert(session, community_name, posts_cached, ttl_seconds, quality_score)
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await _upsert(
            scoped_session, community_name, posts_cached, ttl_seconds, quality_score
        )
        await scoped_session.commit()


async def _upsert(
    session: AsyncSession,
    community_name: str,
    posts_cached: int,
    ttl_seconds: int,
    quality_score: float | None,
) -> None:
    now = datetime.now(timezone.utc)
    instance: Optional[CommunityCache] = await session.get(
        CommunityCache, community_name
    )
    quality_value = (
        Decimal(str(quality_score)) if quality_score is not None else Decimal("0.50")
    )

    if instance is None:
        instance = CommunityCache(
            community_name=community_name,
            last_crawled_at=now,
            posts_cached=posts_cached,
            ttl_seconds=ttl_seconds,
            quality_score=quality_value,
            hit_count=0,
            crawl_priority=50,
        )
        session.add(instance)
    else:
        instance.last_crawled_at = now
        instance.posts_cached = posts_cached
        instance.ttl_seconds = ttl_seconds
        instance.quality_score = quality_value
        instance.updated_at = now


__all__ = ["upsert_community_cache"]


async def mark_crawl_attempt(
    community_name: str,
    *,
    attempted_at: datetime | None = None,
    session: AsyncSession | None = None,
) -> None:
    """记录“尝试过但不代表成功”的时间戳（last_attempt_at）。"""
    ts = attempted_at or datetime.now(timezone.utc)
    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET last_attempt_at = :ts,
                    updated_at = now()
                WHERE community_name = :name
                """
            ),
            {"ts": ts, "name": community_name},
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await mark_crawl_attempt(community_name, attempted_at=ts, session=scoped_session)
        await scoped_session.commit()


async def update_incremental_waterline_if_forward(
    community_name: str,
    *,
    last_seen_post_id: str,
    last_seen_created_at: datetime,
    session: AsyncSession | None = None,
) -> None:
    """
    增量水位线别名层（incremental_waterline）。

    口径：复用 community_cache.last_seen_post_id / last_seen_created_at，
    只允许“往前走”，避免并发写回导致回退。
    """
    if last_seen_created_at.tzinfo is None:
        last_seen_created_at = last_seen_created_at.replace(tzinfo=timezone.utc)

    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET last_seen_created_at = CASE
                        WHEN last_seen_created_at IS NULL OR last_seen_created_at < :created_at
                            THEN :created_at
                        ELSE last_seen_created_at
                    END,
                    last_seen_post_id = CASE
                        WHEN last_seen_created_at IS NULL OR last_seen_created_at < :created_at
                            THEN :post_id
                        ELSE last_seen_post_id
                    END,
                    updated_at = now()
                WHERE community_name = :name
                """
            ),
            {
                "created_at": last_seen_created_at,
                "post_id": last_seen_post_id,
                "name": community_name,
            },
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await update_incremental_waterline_if_forward(
            community_name,
            last_seen_post_id=last_seen_post_id,
            last_seen_created_at=last_seen_created_at,
            session=scoped_session,
        )
        await scoped_session.commit()


async def update_backfill_floor_if_lower(
    community_name: str,
    *,
    backfill_floor: datetime,
    session: AsyncSession | None = None,
) -> None:
    """
    回填底线（backfill_floor）：
    - 越补越老（时间越小）
    - 只允许往“更老”方向推进，避免回填切片并发导致底线被抬高
    """
    if backfill_floor.tzinfo is None:
        backfill_floor = backfill_floor.replace(tzinfo=timezone.utc)

    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET backfill_floor = CASE
                        WHEN backfill_floor IS NULL OR backfill_floor > :floor
                            THEN :floor
                        ELSE backfill_floor
                    END,
                    updated_at = now()
                WHERE community_name = :name
                """
            ),
            {"floor": backfill_floor, "name": community_name},
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await update_backfill_floor_if_lower(
            community_name,
            backfill_floor=backfill_floor,
            session=scoped_session,
        )
        await scoped_session.commit()


async def update_backfill_cursor(
    community_name: str,
    *,
    cursor_after: str | None,
    cursor_created_at: datetime | None,
    session: AsyncSession | None = None,
) -> None:
    """Persist backfill cursor checkpoint for resume."""
    if cursor_created_at is not None and cursor_created_at.tzinfo is None:
        cursor_created_at = cursor_created_at.replace(tzinfo=timezone.utc)
    if cursor_created_at is None and cursor_after is None:
        return

    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET backfill_cursor = :cursor_after,
                    backfill_cursor_created_at = :cursor_created_at,
                    backfill_updated_at = now()
                WHERE community_name = :name
                """
            ),
            {
                "cursor_after": cursor_after,
                "cursor_created_at": cursor_created_at,
                "name": community_name,
            },
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await update_backfill_cursor(
            community_name,
            cursor_after=cursor_after,
            cursor_created_at=cursor_created_at,
            session=scoped_session,
        )
        await scoped_session.commit()


async def mark_backfill_running(
    community_name: str,
    *,
    session: AsyncSession | None = None,
) -> None:
    """Mark backfill as running for a community."""
    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET backfill_status = 'RUNNING',
                    backfill_updated_at = now()
                WHERE community_name = :name
                """
            ),
            {"name": community_name},
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await mark_backfill_running(community_name, session=scoped_session)
        await scoped_session.commit()


async def mark_backfill_status_only(
    community_name: str,
    *,
    status: str,
    session: AsyncSession | None = None,
) -> None:
    """Update only backfill_status (no counters)."""
    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET backfill_status = :status,
                    backfill_updated_at = now()
                WHERE community_name = :name
                """
            ),
            {"name": community_name, "status": status},
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await mark_backfill_status_only(
            community_name,
            status=status,
            session=scoped_session,
        )
        await scoped_session.commit()


async def update_backfill_status(
    community_name: str,
    *,
    status: str,
    coverage_months: int | None,
    sample_posts: int | None,
    sample_comments: int | None,
    backfill_capped: bool | None,
    cursor_after: str | None,
    cursor_created_at: datetime | None,
    session: AsyncSession | None = None,
) -> None:
    """Update backfill status + coverage + sample counters."""
    if cursor_created_at is not None and cursor_created_at.tzinfo is None:
        cursor_created_at = cursor_created_at.replace(tzinfo=timezone.utc)

    payload = {
        "name": community_name,
        "status": status,
        "coverage_months": coverage_months,
        "sample_posts": sample_posts,
        "sample_comments": sample_comments,
        "backfill_capped": backfill_capped,
        "cursor_after": cursor_after,
        "cursor_created_at": cursor_created_at,
    }

    if session is not None:
        await session.execute(
            text(
                """
                UPDATE community_cache
                SET backfill_status = :status,
                    coverage_months = :coverage_months,
                    sample_posts = :sample_posts,
                    sample_comments = :sample_comments,
                    backfill_capped = :backfill_capped,
                    backfill_cursor = COALESCE(CAST(:cursor_after AS text), backfill_cursor),
                    backfill_cursor_created_at = COALESCE(
                        CAST(:cursor_created_at AS timestamptz),
                        backfill_cursor_created_at
                    ),
                    backfill_updated_at = now()
                WHERE community_name = :name
                """
            ),
            payload,
        )
        await session.flush()
        return

    async with SessionFactory() as scoped_session:
        await update_backfill_status(session=scoped_session, **payload)
        await scoped_session.commit()


__all__ += [
    "mark_crawl_attempt",
    "update_incremental_waterline_if_forward",
    "update_backfill_floor_if_lower",
    "update_backfill_cursor",
    "mark_backfill_running",
    "mark_backfill_status_only",
    "update_backfill_status",
]
