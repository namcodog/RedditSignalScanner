from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select

from app.db.session import get_session
from app.models.community_pool import CommunityPool


@dataclass(frozen=True)
class CommunityProfile:
    name: str
    tier: str
    categories: List[str]
    description_keywords: List[str]
    daily_posts: int
    avg_comment_length: int
    quality_score: float
    priority: str


class CommunityPoolLoader:
    """Load and cache community pool from JSON/DB with hourly refresh.

    PRD alignment: Day13 tasks (seed loading, DB import, cached reads).
    """

    def __init__(self, *, seed_path: Optional[Path] = None) -> None:
        self._cache: List[CommunityProfile] = []
        self._last_refresh: Optional[datetime] = None
        self._refresh_interval = timedelta(hours=1)
        self._seed_path = seed_path or Path("backend/config/seed_communities.json")

    def _should_refresh(self) -> bool:
        if self._last_refresh is None:
            return True
        return datetime.now(timezone.utc) - self._last_refresh >= self._refresh_interval

    async def load_seed_communities(self) -> List[Dict[str, Any]]:
        if not self._seed_path.exists():
            return []
        raw = json.loads(self._seed_path.read_text(encoding="utf-8"))
        items = raw.get("seed_communities") or []
        return list(items)

    async def import_to_database(self) -> int:
        """Import seed communities into DB if not existing. Returns inserted count."""
        seed_communities = await self.load_seed_communities()
        if not seed_communities:
            return 0
        inserted = 0
        async for session in get_session():
            for community_data in seed_communities:
                name = str(community_data.get("name", "")).strip()
                if not name:
                    continue
                exists = await session.execute(select(CommunityPool).where(CommunityPool.name == name))
                if exists.scalar_one_or_none() is None:
                    payload = {
                        "name": name,
                        "tier": community_data.get("tier", "default"),
                        "categories": community_data.get("categories", []),
                        "description_keywords": community_data.get("description_keywords", []),
                        "daily_posts": int(community_data.get("daily_posts", 0) or 0),
                        "avg_comment_length": int(community_data.get("avg_comment_length", 0) or 0),
                        "quality_score": float(community_data.get("quality_score", 0.5) or 0.5),
                        "priority": community_data.get("priority", "medium"),
                    }
                    session.add(CommunityPool(**payload))
                    inserted += 1
            await session.commit()
        return inserted

    async def load_community_pool(self, *, force_refresh: bool = False) -> List[CommunityProfile]:
        if force_refresh or self._should_refresh():
            async for session in get_session():
                result = await session.execute(select(CommunityPool).where(CommunityPool.is_active == True))
                rows = result.scalars().all()
                self._cache = [self._to_profile(row) for row in rows]
                self._last_refresh = datetime.now(timezone.utc)
        return list(self._cache)

    async def get_community_by_name(self, name: str) -> Optional[CommunityProfile]:
        items = await self.load_community_pool()
        lower = name.strip().lower()
        for item in items:
            if item.name.lower() == lower:
                return item
        return None

    async def get_communities_by_tier(self, tier: str) -> List[CommunityProfile]:
        items = await self.load_community_pool()
        key = tier.strip().lower()
        return [c for c in items if c.tier.strip().lower() == key]

    @staticmethod
    def _to_profile(row: CommunityPool) -> CommunityProfile:
        return CommunityProfile(
            name=row.name,
            tier=row.tier,
            categories=list(row.categories or []),
            description_keywords=list(row.description_keywords or []),
            daily_posts=int(row.daily_posts or 0),
            avg_comment_length=int(row.avg_comment_length or 0),
            quality_score=float(row.quality_score or 0.0),
            priority=str(row.priority or "medium"),
        )
