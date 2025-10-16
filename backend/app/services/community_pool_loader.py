"""Community Pool Loader Service.

Loads seed communities from JSON file and initializes community cache.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommunityProfile:
    """Community profile data class."""

    name: str
    tier: str
    categories: list[str]
    description_keywords: dict[str, Any]
    daily_posts: int
    avg_comment_length: int
    quality_score: float
    priority: str


class CommunityPoolLoader:
    """Service for loading seed communities and initializing cache."""

    def __init__(self, db: AsyncSession, seed_path: Path | None = None) -> None:
        """Initialize the loader.

        Args:
            db: Database session
            seed_path: Optional path to seed file
        """
        self.db = db
        self._cache: list[CommunityProfile] = []
        self._last_refresh: datetime | None = None
        self._refresh_interval = timedelta(hours=1)
        self.seed_file = seed_path or (
            Path(__file__).parents[2] / "data" / "seed_communities.json"
        )

    def _should_refresh(self) -> bool:
        """Check if cache should be refreshed."""
        if self._last_refresh is None:
            return True
        return datetime.now(timezone.utc) - self._last_refresh >= self._refresh_interval

    async def load_seed_communities(self) -> dict[str, Any]:
        """Load seed communities from JSON file into community_pool table.

        Returns:
            dict: Statistics about loaded communities

        Raises:
            FileNotFoundError: If seed file doesn't exist
            ValueError: If JSON is invalid
        """
        logger.info(f"Loading seed communities from {self.seed_file}")

        # Read seed file
        if not self.seed_file.exists():
            raise FileNotFoundError(f"Seed file not found: {self.seed_file}")

        try:
            with open(self.seed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in seed file: {e}") from e

        communities = data.get("communities", [])
        if not communities:
            raise ValueError("No communities found in seed file")

        logger.info(f"Found {len(communities)} communities in seed file")

        # Load communities into database
        loaded_count = 0
        updated_count = 0

        for community_data in communities:
            name = community_data["name"]

            # Check if community already exists
            stmt = select(CommunityPool).where(CommunityPool.name == name)
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing community
                existing.tier = community_data["tier"]
                existing.priority = community_data["priority"]
                existing.categories = community_data["categories"]
                existing.description_keywords = community_data["description_keywords"]
                existing.daily_posts = community_data["estimated_daily_posts"]
                existing.quality_score = community_data["quality_score"]
                updated_count += 1
                logger.debug(f"Updated existing community: {name}")
            else:
                # Create new community
                community = CommunityPool(
                    name=name,
                    tier=community_data["tier"],
                    priority=community_data["priority"],
                    categories=community_data["categories"],
                    description_keywords=community_data["description_keywords"],
                    daily_posts=community_data["estimated_daily_posts"],
                    avg_comment_length=100,  # Default value
                    quality_score=community_data["quality_score"],
                    is_active=True,
                )
                self.db.add(community)
                loaded_count += 1
                logger.debug(f"Loaded new community: {name}")

        # Commit all changes
        await self.db.commit()

        stats = {
            "total_in_file": len(communities),
            "loaded": loaded_count,
            "updated": updated_count,
            "total_in_db": loaded_count + updated_count,
        }

        logger.info(
            f"Community pool loading complete: "
            f"{loaded_count} loaded, {updated_count} updated"
        )

        return stats

    async def initialize_community_cache(
        self, communities: list[str] | None = None
    ) -> dict[str, Any]:
        """Initialize community cache metadata for communities.

        Args:
            communities: List of community names to initialize.
                        If None, initializes all communities in pool.

        Returns:
            dict: Statistics about initialized cache entries
        """
        logger.info("Initializing community cache metadata")

        # Get communities to initialize
        if communities is None:
            # Get all active communities from pool
            stmt = select(CommunityPool).where(CommunityPool.is_active == True)  # noqa: E712
            result = await self.db.execute(stmt)
            pool_communities = result.scalars().all()
            community_names = [c.name for c in pool_communities]
        else:
            community_names = communities

        logger.info(f"Initializing cache for {len(community_names)} communities")

        # Initialize cache entries
        initialized_count = 0
        skipped_count = 0

        for name in community_names:
            # Check if cache entry already exists
            cache_stmt = select(CommunityCache).where(CommunityCache.community_name == name)
            cache_result = await self.db.execute(cache_stmt)
            existing = cache_result.scalar_one_or_none()

            if existing:
                skipped_count += 1
                logger.debug(f"Cache entry already exists for: {name}")
                continue

            # Get community from pool for priority info
            pool_stmt = select(CommunityPool).where(CommunityPool.name == name)
            pool_result = await self.db.execute(pool_stmt)
            pool_entry = pool_result.scalar_one_or_none()

            if not pool_entry:
                logger.warning(f"Community not found in pool: {name}")
                continue

            # Determine crawl frequency based on priority
            crawl_frequency_map = {
                "high": 2,  # Every 2 hours
                "medium": 4,  # Every 4 hours
                "low": 6,  # Every 6 hours
            }
            crawl_frequency = crawl_frequency_map.get(pool_entry.priority, 4)

            # Determine crawl priority (0-100)
            priority_map = {
                "high": 90,
                "medium": 60,
                "low": 30,
            }
            crawl_priority = priority_map.get(pool_entry.priority, 50)

            # Create cache entry
            cache_entry = CommunityCache(
                community_name=name,
                last_crawled_at=datetime.now(timezone.utc),
                posts_cached=0,
                ttl_seconds=3600,  # 1 hour default TTL
                quality_score=pool_entry.quality_score,
                hit_count=0,
                crawl_priority=crawl_priority,
                crawl_frequency_hours=crawl_frequency,
                is_active=True,
            )
            self.db.add(cache_entry)
            initialized_count += 1
            logger.debug(f"Initialized cache for: {name}")

        # Commit all changes
        await self.db.commit()

        stats = {
            "total_communities": len(community_names),
            "initialized": initialized_count,
            "skipped": skipped_count,
        }

        logger.info(
            f"Cache initialization complete: "
            f"{initialized_count} initialized, {skipped_count} skipped"
        )

        return stats

    async def load_community_pool(
        self, force_refresh: bool = False
    ) -> list[CommunityProfile]:
        """Load community pool from database with caching.

        Args:
            force_refresh: Force refresh cache

        Returns:
            list: List of community profiles
        """
        if force_refresh or self._should_refresh():
            stmt = select(CommunityPool).where(CommunityPool.is_active == True)  # noqa: E712
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            self._cache = [self._to_profile(row) for row in rows]
            self._last_refresh = datetime.now(timezone.utc)
        return list(self._cache)

    async def get_community_by_name(self, name: str) -> CommunityProfile | None:
        """Get community by name.

        Args:
            name: Community name

        Returns:
            CommunityProfile or None
        """
        items = await self.load_community_pool()
        lower = name.strip().lower()
        for item in items:
            if item.name.lower() == lower:
                return item
        return None

    async def get_communities_by_tier(self, tier: str) -> list[CommunityProfile]:
        """Get communities by tier.

        Args:
            tier: Tier name

        Returns:
            list: List of communities
        """
        items = await self.load_community_pool()
        key = tier.strip().lower()
        return [c for c in items if c.tier.strip().lower() == key]

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get statistics about the community pool.

        Returns:
            dict: Pool statistics
        """
        # Count total communities
        stmt = select(CommunityPool)
        result = await self.db.execute(stmt)
        all_communities = result.scalars().all()

        # Count by priority
        high_priority = sum(1 for c in all_communities if c.priority == "high")
        medium_priority = sum(1 for c in all_communities if c.priority == "medium")
        low_priority = sum(1 for c in all_communities if c.priority == "low")

        # Count active
        active = sum(1 for c in all_communities if c.is_active)

        # Calculate average quality score
        avg_quality = (
            sum(c.quality_score for c in all_communities) / len(all_communities)
            if all_communities
            else 0.0
        )

        return {
            "total_communities": len(all_communities),
            "active_communities": active,
            "inactive_communities": len(all_communities) - active,
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "avg_quality_score": round(avg_quality, 2),
        }

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about the community cache.

        Returns:
            dict: Cache statistics
        """
        # Count total cache entries
        stmt = select(CommunityCache)
        result = await self.db.execute(stmt)
        all_entries = result.scalars().all()

        # Count active
        active = sum(1 for e in all_entries if e.is_active)

        # Calculate totals
        total_posts = sum(e.posts_cached for e in all_entries)
        total_hits = sum(e.hit_count for e in all_entries)

        # Calculate average quality score
        avg_quality = (
            sum(e.quality_score for e in all_entries) / len(all_entries)
            if all_entries
            else 0.0
        )

        return {
            "total_entries": len(all_entries),
            "active_entries": active,
            "inactive_entries": len(all_entries) - active,
            "total_posts_cached": total_posts,
            "total_cache_hits": total_hits,
            "avg_quality_score": round(avg_quality, 2),
        }

    @staticmethod
    def _to_profile(row: CommunityPool) -> CommunityProfile:
        """Convert database row to profile."""
        return CommunityProfile(
            name=row.name,
            tier=row.tier,
            categories=list(row.categories or []),
            description_keywords=row.description_keywords or {},
            daily_posts=int(row.daily_posts or 0),
            avg_comment_length=int(row.avg_comment_length or 0),
            quality_score=float(row.quality_score or 0.0),
            priority=str(row.priority or "medium"),
        )
