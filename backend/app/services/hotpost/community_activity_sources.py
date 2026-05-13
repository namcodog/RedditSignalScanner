from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SUPPLY_CONFIG = PROJECT_ROOT / "backend" / "config" / "hotpost_supply_discovery_v2.yaml"
SUPPLY_COMMUNITY_FIELDS = {
    "primary_communities",
    "candidate_communities",
    "listing_communities",
    "listing_bridge_communities",
}


@dataclass(frozen=True)
class CommunityPoolSnapshot:
    name: str
    tier: str | None = None
    categories: list[str] = field(default_factory=list)
    description_keywords: list[str] = field(default_factory=list)
    daily_posts: int = 0
    quality_score: float = 0.0


@dataclass(frozen=True)
class SupplyCommunitySnapshot:
    scopes: tuple[str, ...] = ()
    topic_clusters: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()


def normalize_community_key(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.lower().startswith("r/"):
        raw = raw[2:]
    return raw.strip().lower()


def display_community_name(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.lower().startswith("r/"):
        return f"r/{raw[2:].strip()}"
    return f"r/{raw}"


def _flatten_text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for nested in value.values():
            items.extend(_flatten_text_values(nested))
        return items
    if isinstance(value, list):
        items = []
        for nested in value:
            items.extend(_flatten_text_values(nested))
        return items
    return [str(value)]


def _pool_snapshot(row: CommunityPool) -> CommunityPoolSnapshot:
    return CommunityPoolSnapshot(
        name=row.name,
        tier=row.tier,
        categories=_flatten_text_values(row.categories),
        description_keywords=_flatten_text_values(row.description_keywords),
        daily_posts=int(row.daily_posts or 0),
        quality_score=float(row.quality_score or 0.0),
    )


async def load_community_pool_snapshots(db: AsyncSession) -> dict[str, CommunityPoolSnapshot]:
    result = await db.execute(
        select(CommunityPool).where(
            CommunityPool.deleted_at.is_(None),
            CommunityPool.is_active.is_(True),
            CommunityPool.is_blacklisted.is_(False),
        )
    )
    rows = result.scalars().all()
    return {normalize_community_key(row.name): _pool_snapshot(row) for row in rows}


def load_supply_community_snapshots(config_path: Path = DEFAULT_SUPPLY_CONFIG) -> dict[str, SupplyCommunitySnapshot]:
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    scopes = payload.get("scopes") or {}
    collected: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"scopes": set(), "topic_clusters": set(), "roles": set()}
    )

    for scope_id, scope_payload in scopes.items():
        topic_clusters = (scope_payload or {}).get("topic_clusters") or {}
        for cluster_id, cluster_payload in topic_clusters.items():
            if not isinstance(cluster_payload, dict):
                continue
            for role in SUPPLY_COMMUNITY_FIELDS:
                for community in cluster_payload.get(role) or []:
                    key = normalize_community_key(community)
                    if not key:
                        continue
                    collected[key]["scopes"].add(str(scope_id))
                    collected[key]["topic_clusters"].add(str(cluster_id))
                    collected[key]["roles"].add(role)

    return {
        key: SupplyCommunitySnapshot(
            scopes=tuple(sorted(values["scopes"])),
            topic_clusters=tuple(sorted(values["topic_clusters"])),
            roles=tuple(sorted(values["roles"])),
        )
        for key, values in collected.items()
    }
