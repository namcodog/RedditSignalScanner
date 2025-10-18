"""
Tiered scheduling service for community crawls (Phase 1 - T1.7).

The service encapsulates the logic previously prototyped via the CLI script:
    * Calculate tier assignments based on rolling avg_valid_posts.
    * Apply crawl frequency and quality_tier updates to community_cache.
    * Provide helpers to fetch communities for a given tier and the crawl
      strategy (limit/sort/time_filter) that should be used.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.blacklist_loader import get_blacklist_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TierDefinition:
    """Configuration for a single tier."""

    name: str
    threshold_min: Decimal
    threshold_max: Decimal | None
    frequency_hours: int
    sort: str
    time_filter: str
    limit: int
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "threshold_min": float(self.threshold_min),
            "threshold_max": float(self.threshold_max) if self.threshold_max else None,
            "frequency_hours": self.frequency_hours,
            "sort": self.sort,
            "time_filter": self.time_filter,
            "limit": self.limit,
            "description": self.description,
        }


TIER_CONFIG: dict[str, TierDefinition] = {
    "tier1": TierDefinition(
        name="高活跃（Tier 1）",
        threshold_min=Decimal("20"),
        threshold_max=None,
        frequency_hours=2,
        sort="new",
        time_filter="week",
        limit=50,
        description="高质量高活跃社区，优先抓取最新内容",
    ),
    "tier2": TierDefinition(
        name="中活跃（Tier 2）",
        threshold_min=Decimal("10"),
        threshold_max=Decimal("20"),
        frequency_hours=6,
        sort="top",
        time_filter="week",
        limit=80,
        description="中等质量社区，平衡热门与新增",
    ),
    "tier3": TierDefinition(
        name="低活跃（Tier 3）",
        threshold_min=Decimal("0"),
        threshold_max=Decimal("10"),
        frequency_hours=24,
        sort="top",
        time_filter="month",
        limit=100,
        description="低活跃社区，覆盖历史内容",
    ),
}


class TieredScheduler:
    """Encapsulates tier assignment logic and database updates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.blacklist = get_blacklist_config()

    async def calculate_assignments(self) -> dict[str, list[str]]:
        """Calculate tier assignments based on avg_valid_posts."""

        pool_stmt: Select[Any] = select(
            CommunityPool.name,
            CommunityPool.is_blacklisted,
            CommunityPool.is_active,
        )
        cache_stmt: Select[Any] = select(
            CommunityCache.community_name,
            CommunityCache.avg_valid_posts,
            CommunityCache.quality_tier,
        )

        pool_rows = (await self.session.execute(pool_stmt)).all()
        cache_rows = (await self.session.execute(cache_stmt)).all()

        quality_map: dict[str, Decimal] = {
            row.community_name: Decimal(str(row.avg_valid_posts or 0))
            for row in cache_rows
        }

        assignments: dict[str, list[str]] = {
            "tier1": [],
            "tier2": [],
            "tier3": [],
            "no_data": [],
            "blacklisted": [],
        }

        for name, is_blacklisted, is_active in pool_rows:
            if not is_active:
                continue

            if is_blacklisted or self.blacklist.is_community_blacklisted(name):
                assignments["blacklisted"].append(name)
                continue

            avg_valid = quality_map.get(name, Decimal("0"))
            if avg_valid <= 0:
                assignments["no_data"].append(name)
                continue

            if avg_valid > TIER_CONFIG["tier1"].threshold_min:
                assignments["tier1"].append(name)
            elif avg_valid > TIER_CONFIG["tier2"].threshold_min:
                assignments["tier2"].append(name)
            else:
                assignments["tier3"].append(name)

        logger.info(
            "Tier assignments calculated: tier1=%s tier2=%s tier3=%s no_data=%s blacklisted=%s",
            len(assignments["tier1"]),
            len(assignments["tier2"]),
            len(assignments["tier3"]),
            len(assignments["no_data"]),
            len(assignments["blacklisted"]),
        )
        return assignments

    async def apply_assignments(self, assignments: dict[str, list[str]]) -> None:
        """Persist crawl frequency and quality_tier to community_cache."""

        now = datetime.now(timezone.utc)
        updated = 0
        for tier_name, communities in assignments.items():
            if tier_name not in TIER_CONFIG:
                continue
            tier_cfg = TIER_CONFIG[tier_name]

            if not communities:
                continue

            stmt = (
                update(CommunityCache)
                .where(CommunityCache.community_name.in_(communities))
                .values(
                    crawl_frequency_hours=tier_cfg.frequency_hours,
                    quality_tier=tier_name,
                    updated_at=now,
                )
            )
            result = await self.session.execute(stmt)
            updated += result.rowcount or 0

        await self.session.commit()
        logger.info("Updated %s community cache rows with tier assignments", updated)

    async def get_communities_for_tier(self, tier: str) -> list[str]:
        """Return the list of community names assigned to a tier."""
        if tier not in TIER_CONFIG:
            raise ValueError(f"Unknown tier: {tier}")

        stmt = select(CommunityCache.community_name).where(
            CommunityCache.quality_tier == tier,
            CommunityCache.is_active.is_(True),
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        logger.debug("Loaded %s communities for %s", len(rows), tier)
        return rows

    def get_config_for_tier(self, tier: str) -> TierDefinition:
        """Expose configuration for the given tier."""
        if tier not in TIER_CONFIG:
            raise ValueError(f"Unknown tier: {tier}")
        return TIER_CONFIG[tier]


__all__ = ["TieredScheduler", "TIER_CONFIG", "TierDefinition"]
