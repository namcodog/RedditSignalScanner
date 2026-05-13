from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hotpost.card_payload_store import load_published_cards
from app.services.hotpost.community_activity_sources import (
    DEFAULT_SUPPLY_CONFIG,
    CommunityPoolSnapshot,
    SupplyCommunitySnapshot,
    display_community_name,
    load_community_pool_snapshots,
    load_supply_community_snapshots,
    normalize_community_key,
)


@dataclass
class CommunityActivity:
    community_name: str
    name_key: str
    card_count: int = 0
    latest_card_at: str | None = None
    lanes: Counter[str] = field(default_factory=Counter)
    source_scopes: Counter[str] = field(default_factory=Counter)
    topic_packs: Counter[str] = field(default_factory=Counter)
    topic_clusters: Counter[str] = field(default_factory=Counter)
    example_card_ids: list[str] = field(default_factory=list)
    example_titles: list[str] = field(default_factory=list)
    pool: CommunityPoolSnapshot | None = None
    supply: SupplyCommunitySnapshot | None = None

    @property
    def source_count(self) -> int:
        return len(set(self.example_card_ids))


def _append_unique(items: list[str], value: object, *, limit: int) -> None:
    text = str(value or "").strip()
    if text and text not in items and len(items) < limit:
        items.append(text)


def _iter_card_communities(card: dict[str, Any]) -> Iterable[str]:
    fields = [
        card.get("top_community"),
        (card.get("preview_quote") or {}).get("community") if isinstance(card.get("preview_quote"), dict) else None,
    ]
    source_module = card.get("source_module") or {}
    if isinstance(source_module, dict):
        fields.append(source_module.get("top_community"))
        primary = source_module.get("primary_communities")
        if isinstance(primary, list):
            fields.extend(primary)
    quotes = card.get("quotes")
    if isinstance(quotes, list):
        for quote in quotes:
            if isinstance(quote, dict):
                fields.append(quote.get("community"))

    seen: set[str] = set()
    for value in fields:
        key = normalize_community_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        yield display_community_name(value)


def build_community_activity(
    cards: Iterable[dict[str, Any]],
    *,
    pool_snapshots: dict[str, CommunityPoolSnapshot] | None = None,
    supply_snapshots: dict[str, SupplyCommunitySnapshot] | None = None,
) -> dict[str, CommunityActivity]:
    pool_snapshots = pool_snapshots or {}
    supply_snapshots = supply_snapshots or {}
    activity: dict[str, CommunityActivity] = {}

    for card in cards:
        card_id = str(card.get("card_id") or "").strip()
        title = str(card.get("title") or "").strip()
        published_at = str(card.get("published_at") or card.get("source_event_at") or "").strip()
        lane = str(card.get("lane") or card.get("card_type") or "unknown").strip() or "unknown"
        source_scope = str(card.get("source_scope_id") or "").strip()
        topic_pack = str(card.get("topic_pack_id") or "").strip()
        topic_clusters = _card_topic_clusters(card)

        for community_name in _iter_card_communities(card):
            key = normalize_community_key(community_name)
            item = activity.get(key)
            if item is None:
                item = CommunityActivity(
                    community_name=community_name,
                    name_key=key,
                    pool=pool_snapshots.get(key),
                    supply=supply_snapshots.get(key),
                )
                activity[key] = item
            item.card_count += 1
            item.lanes[lane] += 1
            if source_scope:
                item.source_scopes[source_scope] += 1
            if topic_pack:
                item.topic_packs[topic_pack] += 1
            for topic_cluster in topic_clusters:
                item.topic_clusters[topic_cluster] += 1
            if published_at and (item.latest_card_at is None or published_at > item.latest_card_at):
                item.latest_card_at = published_at
            _append_unique(item.example_card_ids, card_id, limit=5)
            _append_unique(item.example_titles, title, limit=3)

    for key, pool in pool_snapshots.items():
        if key not in activity:
            activity[key] = CommunityActivity(
                community_name=pool.name,
                name_key=key,
                pool=pool,
                supply=supply_snapshots.get(key),
            )
    for key, supply in supply_snapshots.items():
        if key not in activity:
            activity[key] = CommunityActivity(
                community_name=display_community_name(key),
                name_key=key,
                supply=supply,
                pool=pool_snapshots.get(key),
            )
    return activity


def _card_topic_clusters(card: dict[str, Any]) -> tuple[str, ...]:
    values: list[object] = [card.get("topic_cluster_id")]
    raw_ids = card.get("topic_cluster_ids")
    if isinstance(raw_ids, list):
        values.extend(raw_ids)
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return tuple(out)


class HotpostCommunityActivityProvider:
    def __init__(self, *, supply_config_path: Path = DEFAULT_SUPPLY_CONFIG) -> None:
        self._supply_config_path = supply_config_path

    async def load(self, db: AsyncSession) -> dict[str, CommunityActivity]:
        pool_snapshots = await load_community_pool_snapshots(db)
        supply_snapshots = load_supply_community_snapshots(self._supply_config_path)
        return build_community_activity(
            load_published_cards(),
            pool_snapshots=pool_snapshots,
            supply_snapshots=supply_snapshots,
        )


__all__ = [
    "CommunityActivity",
    "CommunityPoolSnapshot",
    "HotpostCommunityActivityProvider",
    "SupplyCommunitySnapshot",
    "build_community_activity",
    "display_community_name",
    "load_community_pool_snapshots",
    "load_supply_community_snapshots",
    "normalize_community_key",
]
