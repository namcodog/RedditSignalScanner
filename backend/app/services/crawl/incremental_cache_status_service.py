from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache


@dataclass(slots=True)
class FailureAttemptInput:
    community_name: str
    now: datetime


@dataclass(slots=True)
class EmptyAttemptInput:
    community_name: str
    now: datetime


@dataclass(slots=True)
class WatermarkUpdateInput:
    community_name: str
    last_seen_post_id: str
    last_seen_created_at: datetime
    total_fetched: int
    new_valid_posts: int
    dedup_rate: float


@dataclass(slots=True)
class IncrementalCacheStatusDeps:
    db: AsyncSession
    now_factory: Callable[[], datetime] = field(
        default=lambda: datetime.now(timezone.utc)
    )


async def record_incremental_failure_attempt(
    update_input: FailureAttemptInput,
    deps: IncrementalCacheStatusDeps,
) -> None:
    await deps.db.execute(
        pg_insert(CommunityCache)
        .values(
            community_name=update_input.community_name,
            last_crawled_at=update_input.now,
            posts_cached=0,
            ttl_seconds=3600,
            quality_score=Decimal("0.50"),
            hit_count=0,
            crawl_priority=50,
            crawl_frequency_hours=2,
            is_active=True,
            empty_hit=0,
            success_hit=0,
            failure_hit=1,
            avg_valid_posts=0,
            quality_tier="medium",
            last_attempt_at=update_input.now,
        )
        .on_conflict_do_update(
            index_elements=["community_name"],
            set_={
                "failure_hit": CommunityCache.failure_hit + 1,
                "last_attempt_at": update_input.now,
            },
        )
    )
    await deps.db.commit()


async def record_incremental_empty_attempt(
    update_input: EmptyAttemptInput,
    deps: IncrementalCacheStatusDeps,
) -> None:
    await deps.db.execute(
        pg_insert(CommunityCache)
        .values(
            community_name=update_input.community_name,
            last_crawled_at=update_input.now,
        )
        .on_conflict_do_update(
            index_elements=["community_name"],
            set_={
                "empty_hit": CommunityCache.empty_hit + 1,
                "last_crawled_at": update_input.now,
            },
        )
    )
    await deps.db.commit()


async def update_incremental_watermark(
    update_input: WatermarkUpdateInput,
    deps: IncrementalCacheStatusDeps,
) -> None:
    now = deps.now_factory()
    await deps.db.execute(
        pg_insert(CommunityCache)
        .values(
            community_name=update_input.community_name,
            quality_tier="medium",
            last_seen_post_id=update_input.last_seen_post_id,
            last_seen_created_at=update_input.last_seen_created_at,
            total_posts_fetched=update_input.total_fetched,
            dedup_rate=update_input.dedup_rate,
            last_crawled_at=now,
            success_hit=1,
            avg_valid_posts=update_input.new_valid_posts,
        )
        .on_conflict_do_update(
            index_elements=["community_name"],
            set_={
                "last_seen_post_id": update_input.last_seen_post_id,
                "last_seen_created_at": update_input.last_seen_created_at,
                "total_posts_fetched": CommunityCache.total_posts_fetched
                + update_input.total_fetched,
                "dedup_rate": update_input.dedup_rate,
                "last_crawled_at": now,
                "success_hit": CommunityCache.success_hit + 1,
                "avg_valid_posts": update_input.new_valid_posts,
                "quality_tier": CommunityCache.quality_tier,
            },
        )
    )
    await deps.db.commit()


__all__ = [
    "EmptyAttemptInput",
    "FailureAttemptInput",
    "IncrementalCacheStatusDeps",
    "WatermarkUpdateInput",
    "record_incremental_empty_attempt",
    "record_incremental_failure_attempt",
    "update_incremental_watermark",
]

