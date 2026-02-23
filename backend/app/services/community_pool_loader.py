"""Community Pool Loader Service.

Loads seed communities from JSON file and initializes community cache.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community_category_map_service import replace_community_category_map

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
        default_seed = (
            Path(__file__).parents[2] / "data" / "community_expansion_200.json"
        )
        if not default_seed.exists():
            default_seed = Path(__file__).parents[2] / "data" / "seed_communities.json"
        self.seed_file = seed_path or default_seed
        # 可选：Top1000 基线（若存在则与 seed 合并去重）
        self.top1000_file = Path(__file__).parents[2] / "data" / "top1000_subreddits.json"
        # 可选：跨境白名单（存在则可启用白名单过滤）
        self.whitelist_file = Path("backend/config/community_whitelist.yaml")

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
        except json.JSONDecodeError as e:  # pragma: no cover - defensive logging
            raise ValueError(f"Invalid JSON in seed file: {e}") from e

        if isinstance(data, list):
            raw_communities = data
        elif isinstance(data, dict):
            raw_communities = data.get("seed_communities", data.get("communities", []))
        else:
            raw_communities = []

        # 可选合并：Top1000 基线（允许字符串列表或对象列表）
        # 隔离模式可通过环境变量禁用：DISABLE_TOP1000_BASELINE=1
        disable_top = str(os.getenv("DISABLE_TOP1000_BASELINE", "")).strip().lower() in {"1", "true", "yes"}
        if self.top1000_file.exists() and not disable_top:
            try:
                with open(self.top1000_file, "r", encoding="utf-8") as f:
                    top_data = json.load(f)
                if isinstance(top_data, dict):
                    top_raw = top_data.get("communities", top_data.get("seed_communities", []))
                else:
                    top_raw = top_data
                # 将字符串条目转为对象结构
                normalized_top: list[dict[str, Any]] = []
                for item in (top_raw or []):
                    if isinstance(item, str):
                        normalized_top.append({"name": item})
                    elif isinstance(item, dict):
                        normalized_top.append(item)
                # 可选：白名单过滤（环境变量 ENFORCE_COMMUNITY_WHITELIST=1 生效）
                enforce_whitelist = str(os.getenv("ENFORCE_COMMUNITY_WHITELIST", "")).strip().lower() in {"1", "true", "yes"}
                whitelist: set[str] = set()
                if enforce_whitelist and self.whitelist_file.exists():
                    try:
                        import yaml as _yaml  # 延迟导入
                        conf = _yaml.safe_load(self.whitelist_file.read_text(encoding="utf-8")) or {}
                        for n in conf.get("communities", []) or []:
                            if isinstance(n, str) and n.strip():
                                wl = n if n.startswith("r/") else f"r/{n}"
                                whitelist.add(wl.lower())
                    except Exception:  # pragma: no cover - 防御性降级
                        whitelist = set()
                if whitelist:
                    normalized_top = [
                        entry for entry in normalized_top
                        if str(entry.get("name", "")).strip().lower() in whitelist or (
                            f"r/{str(entry.get('name','')).strip()}".lower() in whitelist
                        )
                    ]
                # 合并（name 去重，seed 优先，top1000 作为补充）
                seen: set[str] = set()
                merged: list[dict[str, Any]] = []
                # 先放 seed
                for entry in raw_communities:
                    n = str((entry or {}).get("name", "")).strip()
                    if n and not n.startswith("r/"):
                        n = f"r/{n}"
                    if n and n.lower() not in seen:
                        seen.add(n.lower())
                        merged.append(entry)
                # 再补 top1000 缺失项，赋默认属性
                for entry in normalized_top:
                    n = str((entry or {}).get("name", "")).strip()
                    if n and not n.startswith("r/"):
                        n = f"r/{n}"
                    if not n or n.lower() in seen:
                        continue
                    seen.add(n.lower())
                    merged.append(
                        {
                            "name": n,
                            "tier": entry.get("tier", "medium"),
                            "priority": entry.get("priority", "medium"),
                            "categories": entry.get("categories", []),
                            "description_keywords": entry.get("description_keywords", {}),
                            "estimated_daily_posts": int(entry.get("estimated_daily_posts", entry.get("daily_posts", 0)) or 0),
                            "avg_comment_length": int(entry.get("avg_comment_length", 100) or 100),
                            "quality_score": float(entry.get("quality_score", 0.6) or 0.6),
                            "is_active": bool(entry.get("is_active", True)),
                        }
                    )
                raw_communities = merged
            except Exception:
                # 合并失败不阻断主流程
                logger.exception("Failed to merge top1000_subreddits.json; proceeding with seed only")
        elif self.top1000_file.exists() and disable_top:
            logger.info("Top1000 baseline merge disabled by DISABLE_TOP1000_BASELINE; proceeding with seed only")

        if not raw_communities:
            raise ValueError("No communities found in seed file")

        communities = [self._normalize_seed_entry(entry) for entry in raw_communities]

        logger.info(f"Found {len(communities)} communities in seed file")

        # Load communities into database
        loaded_count = 0
        updated_count = 0

        pending_map_updates: list[tuple[CommunityPool, object | None]] = []

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
                existing.description_keywords = community_data["description_keywords"]
                existing.daily_posts = community_data["estimated_daily_posts"]
                existing.avg_comment_length = community_data["avg_comment_length"]
                existing.quality_score = community_data["quality_score"]
                existing.is_active = community_data["is_active"]
                # Clear soft delete markers so the community becomes visible again
                existing.deleted_at = None
                existing.deleted_by = None
                existing.updated_at = datetime.now(timezone.utc)
                updated_count += 1
                pending_map_updates.append((existing, community_data.get("categories")))
                logger.debug(f"Updated existing community: {name}")
            else:
                # Create new community
                community = CommunityPool(
                    name=name,
                    tier=community_data["tier"],
                    priority=community_data["priority"],
                    categories=[],
                    description_keywords=community_data["description_keywords"],
                    daily_posts=community_data["estimated_daily_posts"],
                    avg_comment_length=community_data["avg_comment_length"],
                    quality_score=community_data["quality_score"],
                    is_active=community_data["is_active"],
                )
                self.db.add(community)
                pending_map_updates.append((community, community_data.get("categories")))
                loaded_count += 1
                logger.debug(f"Loaded new community: {name}")

        await self.db.flush()
        for pool, categories in pending_map_updates:
            await replace_community_category_map(
                self.db,
                community_id=pool.id,
                categories=categories,
            )

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
            stmt = select(CommunityPool).where(
                CommunityPool.is_active == True
            )  # noqa: E712
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
            cache_stmt = select(CommunityCache).where(
                CommunityCache.community_name == name
            )
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
            stmt = select(CommunityPool).where(
                CommunityPool.is_active == True,  # noqa: E712
                CommunityPool.is_blacklisted == False,  # noqa: E712
            )  # noqa: E712
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            self._cache = [self._to_profile(row) for row in rows]
            self._last_refresh = datetime.now(timezone.utc)
        return list(self._cache)

    async def get_due_communities(
        self, buffer_minutes: int = 5
    ) -> list[CommunityProfile]:
        """
        返回“到期需要抓取”的社区列表。

        逻辑：
        - 仅返回 last_crawled_at + crawl_frequency_hours 已过期（预留 buffer）的社区
        - 同时要求 CommunityPool/CommunityCache 均为活跃
        """
        now = datetime.now(timezone.utc)
        buffer_delta = timedelta(minutes=max(buffer_minutes, 0))

        stmt = (
            select(CommunityPool, CommunityCache)
            .join(CommunityCache, CommunityPool.name == CommunityCache.community_name, isouter=True)
            .where(CommunityPool.is_active == True)  # noqa: E712
            .where(CommunityPool.is_blacklisted == False)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        due: list[CommunityProfile] = []
        for pool_row, cache_row in rows:
            # 无缓存记录时视为立即到期（首轮抓取）
            last_crawled = getattr(cache_row, "last_crawled_at", None)
            freq_hours = getattr(cache_row, "crawl_frequency_hours", None)
            cache_active = getattr(cache_row, "is_active", True)

            if cache_row is not None and not cache_active:
                continue

            # 当频率缺失时默认 2 小时
            freq_hours = int(freq_hours or 2)
            due_at = (
                last_crawled + timedelta(hours=freq_hours)
                if last_crawled is not None
                else now - timedelta(seconds=1)
            )

            if now + buffer_delta >= due_at:
                due.append(self._to_profile(pool_row))

        return due

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

    @staticmethod
    def _normalize_seed_entry(entry: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw seed entry to loader-friendly structure."""
        name = str(entry.get("name", "")).strip()
        if not name:
            raise ValueError("Seed entry missing community name")

        # Ensure name starts with r/ (database constraint requirement)
        if not name.startswith("r/"):
            name = f"r/{name}"

        tier = str(entry.get("tier", "medium")).lower()
        if tier not in {"high", "medium", "low"}:
            tier = "medium"

        priority = entry.get("priority")
        if isinstance(priority, str):
            priority = priority.lower()
        if priority not in {"high", "medium", "low"}:
            priority = tier

        estimated = entry.get("estimated_daily_posts", entry.get("daily_posts", 0))
        try:
            estimated_posts = int(estimated)
        except (TypeError, ValueError):
            estimated_posts = 0

        avg_comment = entry.get("avg_comment_length", 100)
        try:
            avg_comment_length = int(avg_comment)
        except (TypeError, ValueError):
            avg_comment_length = 100

        categories_raw = entry.get("categories", [])
        if isinstance(categories_raw, dict):
            categories = list(categories_raw.keys())
        elif isinstance(categories_raw, list):
            categories = categories_raw
        else:
            categories = [str(categories_raw)]

        keywords_raw = entry.get("description_keywords", {})
        if isinstance(keywords_raw, dict):
            description_keywords = keywords_raw
        elif isinstance(keywords_raw, list):
            description_keywords = {str(key): 1.0 for key in keywords_raw}
        else:
            description_keywords = {}

        quality = entry.get("quality_score", 0.5)
        try:
            quality_score = float(quality)
        except (TypeError, ValueError):
            quality_score = 0.5

        return {
            "name": name,
            "tier": tier,
            "priority": priority,
            "categories": categories,
            "description_keywords": description_keywords,
            "estimated_daily_posts": estimated_posts,
            "avg_comment_length": avg_comment_length,
            "quality_score": quality_score,
            "is_active": bool(entry.get("is_active", True)),
        }
