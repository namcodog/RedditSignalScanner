from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool
from app.services.blacklist_loader import BlacklistConfig
from app.services.community_pool_loader import CommunityProfile
from app.utils.subreddit import normalize_subreddit_name

logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        logger.exception("Failed to load yaml from %s", path)
        return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalize_subreddit(value: str) -> str:
    name = normalize_subreddit_name(value or "")
    return name.lower()


@dataclass(frozen=True)
class CrawlPlanEntry:
    profile: CommunityProfile
    status: str  # active | paused
    role: str | None
    vertical: str | None
    crawl_track: str  # both | posts_only | comments_only | none
    priority: str
    source: str = "community_pool"


class CrawlPlanBuilder:
    """Builds crawl plan from community_pool + YAML configs."""

    def __init__(self, db: AsyncSession, config_root: Path | None = None) -> None:
        self.db = db
        self.config_root = config_root or Path(__file__).resolve().parents[2] / "config"
        self.blacklist = BlacklistConfig(
            str(self.config_root / "community_blacklist.yaml")
        )
        self.role_map = self._load_role_map()
        self.vertical_overrides = self._load_vertical_overrides()

    def _load_role_map(self) -> dict[str, str]:
        data = _load_yaml(self.config_root / "community_roles.yaml")
        role_map: dict[str, str] = {}
        for role_name, conf in (data.get("roles") or {}).items():
            for community in _as_list(conf.get("communities")):
                key = _normalize_subreddit(str(community))
                if key:
                    role_map[key] = role_name
        return role_map

    def _load_vertical_overrides(self) -> dict[str, dict[str, Any]]:
        data = _load_yaml(self.config_root / "vertical_overrides.yaml")
        overrides: dict[str, dict[str, Any]] = {}
        for entry in data.get("overrides", []) or []:
            raw_name = entry.get("subreddit") or entry.get("community")
            key = _normalize_subreddit(str(raw_name or ""))
            if not key:
                continue
            overrides[key] = {
                "vertical": entry.get("vertical"),
                "crawl_track": entry.get("crawl_track"),
                "priority": entry.get("priority"),
            }
        return overrides

    def _derive_vertical(self, categories: Iterable[Any]) -> str | None:
        for item in categories:
            if isinstance(item, str) and item.strip():
                return item
        return None

    async def build_plan(self) -> list[CrawlPlanEntry]:
        stmt = select(CommunityPool)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        plan: list[CrawlPlanEntry] = []
        for row in rows:
            key = _normalize_subreddit(row.name)
            overrides = self.vertical_overrides.get(key, {})
            role = self.role_map.get(key)
            vertical = overrides.get("vertical") or self._derive_vertical(
                _as_list(row.categories)
            )
            crawl_track = overrides.get("crawl_track") or "both"
            priority = overrides.get("priority") or row.priority

            is_blacklisted = bool(row.is_blacklisted)
            if self.blacklist and self.blacklist.is_community_blacklisted(row.name):
                is_blacklisted = True
            status = "paused" if (not row.is_active or is_blacklisted) else "active"

            profile = CommunityProfile(
                name=row.name,
                tier=row.tier,
                categories=_as_list(row.categories),
                description_keywords=row.description_keywords or {},
                daily_posts=row.daily_posts or 0,
                avg_comment_length=row.avg_comment_length or 0,
                quality_score=float(row.quality_score or 0.0),
                priority=priority or "medium",
            )

            plan.append(
                CrawlPlanEntry(
                    profile=profile,
                    status=status,
                    role=role,
                    vertical=vertical,
                    crawl_track=str(crawl_track or "both"),
                    priority=priority or "medium",
                )
            )

        return plan
