from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.community_mutation_state import CommunityMutationState

__all__ = [
    "priority_to_frequency_hours",
    "priority_to_runtime_priority",
    "sync_cache_projection",
    "sync_pool_projection",
]


def priority_to_runtime_priority(priority:Optional[ str]) -> int:
    return {"high": 90, "medium": 60, "low": 30}.get(str(priority or "medium"), 50)


def priority_to_frequency_hours(priority:Optional[ str]) -> int:
    return {"high": 2, "medium": 4, "low": 6}.get(str(priority or "medium"), 4)


def _normalize_keywords(raw:Optional[ object]) -> dict[str, object]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {"keywords": [str(item).strip() for item in raw if str(item).strip()]}
    return {"keywords": []}


async def sync_pool_projection(
    session: AsyncSession,
    *,
    state: CommunityMutationState,
    community_name: str,
    category_keys: list[str],
    tier:Optional[ str],
    priority:Optional[ str],
    description_keywords:Optional[ object],
    quality_score:Optional[ float],
    discovered_count:Optional[ int],
    actor_id: uuid.Optional[UUID],
    runtime_enabled: bool,
    now: datetime,
) -> CommunityPool:
    pool = state.pool
    if pool is None:
        pool = CommunityPool(
            name=community_name,
            tier=tier or "medium",
            categories=category_keys,
            description_keywords=_normalize_keywords(description_keywords),
            daily_posts=0,
            avg_comment_length=0,
            quality_score=quality_score or 0.50,
            priority=priority or "medium",
            user_feedback_count=0,
            discovered_count=int(discovered_count or 0),
            is_active=runtime_enabled,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(pool)
        await session.flush()
    else:
        pool.tier = tier or pool.tier
        pool.priority = priority or pool.priority
        pool.categories = category_keys or pool.categories
        pool.description_keywords = _normalize_keywords(
            description_keywords or pool.description_keywords
        )
        if quality_score is not None:
            pool.quality_score = quality_score
        if discovered_count is not None:
            pool.discovered_count = int(discovered_count)
        pool.is_active = runtime_enabled
        pool.updated_by = actor_id
    if runtime_enabled:
        pool.deleted_at = None
        pool.deleted_by = None
    else:
        pool.deleted_at = now
        pool.deleted_by = actor_id
    return pool


async def sync_cache_projection(
    session: AsyncSession,
    *,
    existing_cache:Optional[ CommunityCache],
    community_name: str,
    priority: str,
    quality_score: float,
    runtime_enabled: bool,
    now: datetime,
) -> None:
    if existing_cache is None and not runtime_enabled:
        return
    if existing_cache is None:
        # projection 仍有旧消费者依赖，因此新增正式社区时要补 cache 元数据。
        session.add(
            CommunityCache(
                community_name=community_name,
                last_crawled_at=now,
                posts_cached=0,
                ttl_seconds=3600,
                quality_score=Decimal(str(quality_score)),
                hit_count=0,
                crawl_priority=priority_to_runtime_priority(priority),
                crawl_frequency_hours=priority_to_frequency_hours(priority),
                is_active=True,
            )
        )
        return
    existing_cache.is_active = runtime_enabled
    existing_cache.crawl_priority = priority_to_runtime_priority(priority)
    existing_cache.crawl_frequency_hours = priority_to_frequency_hours(priority)
    existing_cache.quality_score = Decimal(str(quality_score))
