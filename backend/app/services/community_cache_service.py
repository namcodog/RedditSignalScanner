from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

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
