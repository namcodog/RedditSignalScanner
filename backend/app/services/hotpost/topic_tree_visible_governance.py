from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import ceil
from typing import Any

from app.services.hotpost.topic_tree_governance_common import (
    TopicTreeRecord,
    build_topic_tree_record,
    build_topic_tree_records,
    parse_dt,
)


def build_visible_tree_governance_snapshot(
    *,
    items: list[dict[str, Any]],
    candidate_items: list[dict[str, Any]] | None = None,
    reference_time: datetime | None = None,
) -> dict[str, Any]:
    resolved_reference = reference_time or _reference_time([*items, *(candidate_items or [])])
    records = build_topic_tree_records(items, reference_time=resolved_reference, treat_as_published=True)
    candidate_records = build_topic_tree_records(
        candidate_items or items,
        reference_time=resolved_reference,
        treat_as_published=True,
    )

    scope_counts = Counter(record.source_scope_id for record in records if record.source_scope_id)
    pack_counts = Counter(record.topic_pack_id for record in records if record.topic_pack_id)
    community_counts = Counter(record.community for record in records if record.community)
    available_scopes = sorted({record.source_scope_id for record in candidate_records if record.source_scope_id})

    item_count = len(records)
    scope_share_limit = max(1, ceil(max(item_count, 1) * 0.4))
    pack_share_limit = max(2, ceil(max(item_count, 1) / 3))
    community_limit = 2 if item_count >= 10 else 1 if item_count >= 4 else item_count

    missing_scope_ids = [
        scope_id
        for scope_id in available_scopes
        if scope_counts.get(scope_id, 0) == 0
    ]
    overweight_scope_ids = sorted(
        scope_id for scope_id, count in scope_counts.items() if count > scope_share_limit
    )
    overweight_pack_ids = sorted(
        str(pack_id)
        for pack_id, count in pack_counts.items()
        if pack_id and count > pack_share_limit
    )
    overweight_communities = sorted(
        str(community)
        for community, count in community_counts.items()
        if community and count > community_limit
    )

    top_scope_share = 0.0
    if item_count and scope_counts:
        top_scope_share = max(scope_counts.values()) / item_count
    top_pack_share = 0.0
    if item_count and pack_counts:
        top_pack_share = max(pack_counts.values()) / item_count
    top_community_share = 0.0
    if item_count and community_counts:
        top_community_share = max(community_counts.values()) / item_count

    return {
        "item_count": item_count,
        "available_scope_ids": available_scopes,
        "scope_counts": dict(scope_counts),
        "pack_counts": dict(pack_counts),
        "community_counts": dict(community_counts),
        "missing_scope_ids": missing_scope_ids,
        "overweight_scope_ids": overweight_scope_ids,
        "overweight_pack_ids": overweight_pack_ids,
        "overweight_communities": overweight_communities,
        "new_source_count": sum(1 for record in records if record.is_new_source),
        "top_scope_share": round(top_scope_share, 4),
        "top_pack_share": round(top_pack_share, 4),
        "top_community_share": round(top_community_share, 4),
    }


def visible_tree_governance_score(
    *,
    items: list[dict[str, Any]],
    candidate_items: list[dict[str, Any]],
    reference_time: datetime | None = None,
) -> tuple[Any, ...]:
    snapshot = build_visible_tree_governance_snapshot(
        items=items,
        candidate_items=candidate_items,
        reference_time=reference_time,
    )
    return (
        len(snapshot["missing_scope_ids"]),
        len(snapshot["overweight_communities"]),
        len(snapshot["overweight_pack_ids"]),
        len(snapshot["overweight_scope_ids"]),
        -int(snapshot["new_source_count"]),
        float(snapshot["top_community_share"]),
        float(snapshot["top_pack_share"]),
        float(snapshot["top_scope_share"]),
        -len(items),
    )


def select_governed_window_indices(
    cards: list[dict[str, Any]],
    *,
    window_size: int,
    pool_size: int | None = None,
) -> list[int]:
    if window_size <= 0 or not cards:
        return []

    resolved_reference = _reference_time(cards)
    candidate_limit = min(len(cards), max(pool_size or window_size * 4, window_size))
    pool = cards[:candidate_limit]
    available_scope_ids = sorted(
        {
            record.source_scope_id
            for record in build_topic_tree_records(pool, reference_time=resolved_reference, treat_as_published=True)
            if record.source_scope_id
        }
    )

    selected_indices: list[int] = []
    selected_records: list[TopicTreeRecord] = []
    used_window_keys: set[tuple[str, str]] = set()

    while len(selected_indices) < min(window_size, len(cards)):
        best_index: int | None = None
        best_key: tuple[Any, ...] | None = None
        for index, card in enumerate(cards):
            if index in selected_indices:
                continue
            key = _visible_window_key(card)
            if key in used_window_keys:
                continue
            record = build_topic_tree_record(card, reference_time=resolved_reference, treat_as_published=True)
            selection_key = _governed_selection_key(
                record=record,
                recency_rank=index,
                selected_records=selected_records,
                available_scope_ids=available_scope_ids,
            )
            if best_key is None or selection_key < best_key:
                best_key = selection_key
                best_index = index
        if best_index is None:
            break
        selected_indices.append(best_index)
        used_window_keys.add(_visible_window_key(cards[best_index]))
        selected_records.append(
            build_topic_tree_record(cards[best_index], reference_time=resolved_reference, treat_as_published=True)
        )

    return selected_indices


def _governed_selection_key(
    *,
    record: TopicTreeRecord,
    recency_rank: int,
    selected_records: list[TopicTreeRecord],
    available_scope_ids: list[str],
) -> tuple[Any, ...]:
    selected_scope_counts = Counter(item.source_scope_id for item in selected_records if item.source_scope_id)
    selected_pack_counts = Counter(item.topic_pack_id for item in selected_records if item.topic_pack_id)
    selected_community_counts = Counter(item.community for item in selected_records if item.community)
    selected_event_keys = {item.event_key for item in selected_records if item.event_key}
    selected_angle_counts = Counter(item.angle_key for item in selected_records if item.angle_key)
    selected_scope_ids = {item.source_scope_id for item in selected_records if item.source_scope_id}
    selected_pack_ids = {item.topic_pack_id for item in selected_records if item.topic_pack_id}

    current_size = len(selected_records) + 1
    scope_soft_limit = max(1, ceil(current_size * 0.4))
    pack_soft_limit = max(2, ceil(current_size / 3))

    scope_missing_priority = 1
    if record.source_scope_id and len(selected_scope_ids) < min(len(available_scope_ids), 3):
        scope_missing_priority = 0 if record.source_scope_id not in selected_scope_ids else 1

    pack_missing_priority = 1
    if record.topic_pack_id:
        pack_missing_priority = 0 if record.topic_pack_id not in selected_pack_ids else 1

    community_penalty = max(selected_community_counts.get(record.community, 0) - 1, 0) if record.community else 0
    scope_penalty = max(selected_scope_counts.get(record.source_scope_id, 0) - scope_soft_limit + 1, 0)
    pack_penalty = (
        max(selected_pack_counts.get(record.topic_pack_id, 0) - pack_soft_limit + 1, 0)
        if record.topic_pack_id
        else 0
    )
    event_penalty = 1 if record.event_key and record.event_key in selected_event_keys else 0
    angle_penalty = 1 if record.angle_key and selected_angle_counts.get(record.angle_key, 0) >= 1 else 0
    old_source_penalty = 1 if record.is_old_source and selected_community_counts.get(record.community, 0) >= 1 else 0
    new_source_priority = 0 if record.is_new_source else 1

    return (
        event_penalty,
        angle_penalty,
        community_penalty,
        scope_missing_priority,
        scope_penalty,
        pack_missing_priority,
        pack_penalty,
        old_source_penalty,
        new_source_priority,
        -record.score_hint,
        recency_rank,
        record.title,
    )


def _reference_time(items: list[dict[str, Any]]) -> datetime:
    timestamps = [
        parse_dt(item.get("published_at")) or parse_dt(item.get("source_event_at"))
        for item in items
    ]
    resolved = max((timestamp for timestamp in timestamps if timestamp is not None), default=None)
    return resolved or datetime.now(timezone.utc)


def _visible_window_key(item: dict[str, Any]) -> tuple[str, str]:
    return (
        str(item.get("source_link") or item.get("card_id") or item.get("signal_id") or "").strip(),
        str(item.get("lane") or "").strip(),
    )


__all__ = [
    "build_visible_tree_governance_snapshot",
    "select_governed_window_indices",
    "visible_tree_governance_score",
]
