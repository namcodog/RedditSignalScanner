"""
Targeted recrawl helper utilities (Phase 1 - T1.8).

Provides a reusable query to locate low-quality or stale communities and
helpers to mark empty hits consistently with IncrementalCrawler semantics.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


async def find_low_quality_candidates(
    session: AsyncSession,
    *,
    hours_threshold: int = 8,
    avg_posts_threshold: float = 50,
    limit: int | None = None,
) -> list[str]:
    """
    Locate communities that should be targeted for recrawl.

    Conditions:
        * Active community not in blacklist (CommunityPool.is_blacklisted is False)
        * last_crawled_at is older than `hours_threshold` hours (or NULL)
        * avg_valid_posts lower than provided threshold (or NULL)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)

    stmt = (
        select(CommunityPool.name)
        .join(
            CommunityCache,
            CommunityPool.name == CommunityCache.community_name,
            isouter=True,
        )
        .where(
            and_(
                CommunityPool.is_active.is_(True),
                CommunityPool.is_blacklisted.is_(False),
                (
                    (CommunityCache.last_crawled_at == None)  # noqa: E711
                    | (CommunityCache.last_crawled_at < cutoff)
                ),
                (
                    (CommunityCache.avg_valid_posts == None)  # noqa: E711
                    | (CommunityCache.avg_valid_posts < avg_posts_threshold)
                ),
            )
        )
        .order_by(CommunityCache.last_crawled_at.asc().nullsfirst())
    )

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_empty_hit(
    session: AsyncSession, community_names: Sequence[str]
) -> None:
    """Increment empty_hit for communities where recrawl returned nothing."""
    if not community_names:
        return

    now = datetime.now(timezone.utc)
    stmt = (
        update(CommunityCache)
        .where(CommunityCache.community_name.in_(community_names))
        .values(
            empty_hit=CommunityCache.empty_hit + 1,
            last_crawled_at=now,
            updated_at=now,
        )
    )
    await session.execute(stmt)
    await session.commit()


__all__ = ["find_low_quality_candidates", "mark_empty_hit"]
