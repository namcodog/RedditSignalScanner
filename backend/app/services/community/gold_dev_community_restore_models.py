from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.community_category_map_service import _normalize_category_keys


@dataclass(frozen=True)
class CommunityPoolSnapshot:
    name: str
    tier: str
    categories: list[str]
    description_keywords: dict[str, object]
    daily_posts: int
    avg_comment_length: int
    quality_score: Decimal
    priority: str
    user_feedback_count: int
    discovered_count: int
    is_active: bool
    is_blacklisted: bool
    blacklist_reason:Optional[ str]
    downrank_factor:Optional[ Decimal]
    health_status: str
    last_evaluated_at:Optional[ datetime]
    auto_tier_enabled: bool
    deleted_at:Optional[ datetime]
    deleted_by:Optional[ UUID]


@dataclass(frozen=True)
class CommunityCacheSnapshot:
    community_name: str
    last_crawled_at: datetime
    posts_cached: int
    ttl_seconds: int
    quality_score: Decimal
    hit_count: int
    crawl_priority: int
    last_hit_at:Optional[ datetime]
    crawl_frequency_hours: int
    is_active: bool
    empty_hit: int
    success_hit: int
    failure_hit: int
    avg_valid_posts: int
    quality_tier: str
    last_seen_post_id:Optional[ str]
    last_seen_created_at:Optional[ datetime]
    backfill_floor:Optional[ datetime]
    backfill_status:Optional[ str]
    coverage_months:Optional[ int]
    sample_posts:Optional[ int]
    sample_comments:Optional[ int]
    backfill_capped:Optional[ bool]
    backfill_cursor:Optional[ str]
    backfill_cursor_created_at:Optional[ datetime]
    backfill_updated_at:Optional[ datetime]
    last_attempt_at:Optional[ datetime]
    member_count:Optional[ int]
    total_posts_fetched: int
    dedup_rate:Optional[ Decimal]


@dataclass(frozen=True)
class CommunityRestorePlan:
    pool_snapshots: list[CommunityPoolSnapshot]
    cache_snapshots: list[CommunityCacheSnapshot]
    deactivate_pool_names: list[str]
    deactivate_cache_names: list[str]


@dataclass(frozen=True)
class CommunityRestoreResult:
    pool_upserts: int
    cache_upserts: int
    pool_deactivated: int
    cache_deactivated: int
    truth_registry_retired: int
    truth_runtime_paused: int
    truth_membership_archived: int
    truth_governance_archived: int
    dry_run: bool


def snapshot_pool(pool: CommunityPool) -> CommunityPoolSnapshot:
    return CommunityPoolSnapshot(
        name=pool.name,
        tier=pool.tier,
        categories=_normalize_category_keys(pool.categories),
        description_keywords=dict(pool.description_keywords or {}),
        daily_posts=int(pool.daily_posts or 0),
        avg_comment_length=int(pool.avg_comment_length or 0),
        quality_score=Decimal(str(pool.quality_score or 0)),
        priority=pool.priority,
        user_feedback_count=int(pool.user_feedback_count or 0),
        discovered_count=int(pool.discovered_count or 0),
        is_active=bool(pool.is_active),
        is_blacklisted=bool(pool.is_blacklisted),
        blacklist_reason=pool.blacklist_reason,
        downrank_factor=(
            Decimal(str(pool.downrank_factor)) if pool.downrank_factor is not None else None
        ),
        health_status=pool.health_status,
        last_evaluated_at=pool.last_evaluated_at,
        auto_tier_enabled=bool(pool.auto_tier_enabled),
        deleted_at=pool.deleted_at,
        deleted_by=pool.deleted_by,
    )


def snapshot_cache(cache: CommunityCache) -> CommunityCacheSnapshot:
    return CommunityCacheSnapshot(
        community_name=cache.community_name,
        last_crawled_at=cache.last_crawled_at,
        posts_cached=int(cache.posts_cached or 0),
        ttl_seconds=int(cache.ttl_seconds or 3600),
        quality_score=Decimal(str(cache.quality_score or 0)),
        hit_count=int(cache.hit_count or 0),
        crawl_priority=int(cache.crawl_priority or 50),
        last_hit_at=cache.last_hit_at,
        crawl_frequency_hours=int(cache.crawl_frequency_hours or 2),
        is_active=bool(cache.is_active),
        empty_hit=int(cache.empty_hit or 0),
        success_hit=int(cache.success_hit or 0),
        failure_hit=int(cache.failure_hit or 0),
        avg_valid_posts=int(cache.avg_valid_posts or 0),
        quality_tier=cache.quality_tier,
        last_seen_post_id=cache.last_seen_post_id,
        last_seen_created_at=cache.last_seen_created_at,
        backfill_floor=cache.backfill_floor,
        backfill_status=cache.backfill_status,
        coverage_months=cache.coverage_months,
        sample_posts=cache.sample_posts,
        sample_comments=cache.sample_comments,
        backfill_capped=cache.backfill_capped,
        backfill_cursor=cache.backfill_cursor,
        backfill_cursor_created_at=cache.backfill_cursor_created_at,
        backfill_updated_at=cache.backfill_updated_at,
        last_attempt_at=cache.last_attempt_at,
        member_count=cache.member_count,
        total_posts_fetched=int(cache.total_posts_fetched or 0),
        dedup_rate=Decimal(str(cache.dedup_rate)) if cache.dedup_rate is not None else None,
    )


async def load_gold_community_restore_plan(
    gold_session: AsyncSession,
    dev_session: AsyncSession,
) -> CommunityRestorePlan:
    gold_pools = (
        await gold_session.execute(select(CommunityPool).order_by(CommunityPool.id.asc()))
    ).scalars().all()
    gold_caches = (
        await gold_session.execute(
            select(CommunityCache).order_by(func.lower(CommunityCache.community_name).asc())
        )
    ).scalars().all()
    dev_pool_names = set((await dev_session.execute(select(CommunityPool.name))).scalars().all())
    dev_cache_names = set(
        (await dev_session.execute(select(CommunityCache.community_name))).scalars().all()
    )
    gold_pool_names = {pool.name for pool in gold_pools}
    gold_cache_names = {cache.community_name for cache in gold_caches}
    return CommunityRestorePlan(
        pool_snapshots=[snapshot_pool(pool) for pool in gold_pools],
        cache_snapshots=[snapshot_cache(cache) for cache in gold_caches],
        deactivate_pool_names=sorted(dev_pool_names - gold_pool_names),
        deactivate_cache_names=sorted(dev_cache_names - gold_cache_names),
    )


__all__ = [
    "CommunityCacheSnapshot",
    "CommunityPoolSnapshot",
    "CommunityRestorePlan",
    "CommunityRestoreResult",
    "load_gold_community_restore_plan",
]
