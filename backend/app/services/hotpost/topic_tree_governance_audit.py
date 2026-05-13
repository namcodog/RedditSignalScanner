from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from app.services.hotpost.hotpost_supply_contract import get_scope_topic_pack_contracts, get_supply_scope
from app.services.hotpost.topic_tree_governance_common import TopicTreeRecord, window_records


def build_topic_tree_governance_audit(
    *,
    scope_id: str,
    history_records: list[TopicTreeRecord],
    planned_records: list[TopicTreeRecord],
    candidate_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    allocation = build_tree_coverage_allocation_audit(
        scope_id=scope_id,
        history_records=history_records,
        planned_records=planned_records,
        candidate_records=candidate_records,
        reference_time=reference_time,
    )
    rotation = build_rolling_rotation_cooldown_audit(
        history_records=history_records,
        planned_records=planned_records,
        reference_time=reference_time,
    )
    supply = build_tree_supply_coverage_yield_audit(
        scope_id=scope_id,
        history_records=history_records,
        planned_records=planned_records,
        candidate_records=candidate_records,
        reference_time=reference_time,
    )
    source_health = build_source_health_under_tree_audit(
        scope_id=scope_id,
        history_records=history_records,
        planned_records=planned_records,
        candidate_records=candidate_records,
        reference_time=reference_time,
    )
    decisions = [
        allocation["decision"],
        rotation["decision"],
        supply["decision"],
        source_health["decision"],
    ]
    overall = "publish"
    if "fail" in decisions:
        overall = "fail"
    elif "rewrite" in decisions:
        overall = "rewrite"
    return {
        "scope_id": scope_id,
        "overall_decision": overall,
        "allocation": allocation,
        "rotation": rotation,
        "supply": supply,
        "source_health": source_health,
    }


def build_tree_coverage_allocation_audit(
    *,
    scope_id: str,
    history_records: list[TopicTreeRecord],
    planned_records: list[TopicTreeRecord],
    candidate_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    recent = [*window_records(history_records, reference_time=reference_time, days=3), *planned_records]
    visible_pack_counts = Counter(record.topic_pack_id for record in recent if record.topic_pack_id)
    visible_cluster_counts = Counter(cluster_id for record in recent for cluster_id in _record_cluster_ids(record))
    candidate_pack_counts = Counter(record.topic_pack_id for record in candidate_records if record.topic_pack_id)
    candidate_cluster_counts = Counter(cluster_id for record in candidate_records for cluster_id in _record_cluster_ids(record))
    configured_pack_ids = tuple(sorted(get_scope_topic_pack_contracts(scope_id).keys()))
    missing_pack_ids = [
        pack_id
        for pack_id in configured_pack_ids
        if candidate_pack_counts.get(pack_id, 0) > 0 and visible_pack_counts.get(pack_id, 0) == 0
    ]
    total_visible = sum(visible_pack_counts.values())
    top_pack_share = 0.0
    if total_visible > 0 and visible_pack_counts:
        top_pack_share = max(visible_pack_counts.values()) / total_visible
    decision = "publish"
    if missing_pack_ids:
        decision = "rewrite"
    return {
        "decision": decision,
        "window_days": 3,
        "visible_pack_counts": dict(visible_pack_counts),
        "visible_cluster_counts": dict(visible_cluster_counts),
        "candidate_pack_counts": dict(candidate_pack_counts),
        "candidate_cluster_counts": dict(candidate_cluster_counts),
        "missing_pack_ids": missing_pack_ids,
        "top_pack_share": round(top_pack_share, 4),
        "new_source_visible_count": sum(1 for record in recent if record.is_new_source),
    }


def build_rolling_rotation_cooldown_audit(
    *,
    history_records: list[TopicTreeRecord],
    planned_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    recent_7d = window_records(history_records, reference_time=reference_time, days=7)
    recent_3d = window_records(history_records, reference_time=reference_time, days=3)
    flagged_items: list[dict[str, Any]] = []
    override_count = 0
    for record in planned_records:
        signal = rotation_signal_for_record(
            record=record,
            history_records=recent_7d,
            selected_records=[planned for planned in planned_records if planned.item_id != record.item_id],
            reference_time=reference_time,
        )
        if signal["cooldown_override"]:
            override_count += 1
        if signal["cooldown_penalty"]:
            flagged_items.append(
                {
                    "item_id": record.item_id,
                    "title": record.title,
                    "event_hit": signal["same_event_within_3d"],
                    "angle_hit": signal["same_angle_within_3d"],
                    "community_hit": signal["same_community_recent_count"] >= 2,
                    "named_topic_hit": signal["named_topic_cooldown_hit"],
                }
            )
    decision = "publish" if not flagged_items else "rewrite"
    same_community_counts = Counter(record.community for record in recent_3d if record.community)
    return {
        "decision": decision,
        "window_days": 7,
        "flagged_items": flagged_items,
        "cooldown_override_count": override_count,
        "same_community_recent_counts": dict(same_community_counts),
    }


def build_tree_supply_coverage_yield_audit(
    *,
    scope_id: str,
    history_records: list[TopicTreeRecord],
    planned_records: list[TopicTreeRecord],
    candidate_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    recent_published = window_records(history_records, reference_time=reference_time, days=7)
    unique_supply_pool = _unique_records([*candidate_records, *planned_records])
    publish_pack_counts = Counter(record.topic_pack_id for record in recent_published if record.topic_pack_id)
    publish_cluster_counts = Counter(cluster_id for record in recent_published for cluster_id in _record_cluster_ids(record))
    pool_pack_counts = Counter(record.topic_pack_id for record in unique_supply_pool if record.topic_pack_id)
    pool_cluster_counts = Counter(cluster_id for record in unique_supply_pool for cluster_id in _record_cluster_ids(record))
    configured_pack_ids = tuple(sorted(get_scope_topic_pack_contracts(scope_id).keys()))
    configured_cluster_ids = tuple(sorted(dict(get_supply_scope(scope_id).get("topic_clusters") or {}).keys()))
    supply_gap_packs = sorted(
        pack_id for pack_id in configured_pack_ids if pool_pack_counts.get(pack_id, 0) == 0 and publish_pack_counts.get(pack_id, 0) == 0
    )
    blocked_supply_packs = sorted(
        pack_id for pack_id in configured_pack_ids if pool_pack_counts.get(pack_id, 0) > 0 and publish_pack_counts.get(pack_id, 0) == 0
    )
    blocked_supply_clusters = sorted(
        cluster_id
        for cluster_id in configured_cluster_ids
        if pool_cluster_counts.get(cluster_id, 0) > 0 and publish_cluster_counts.get(cluster_id, 0) == 0
    )
    half_healthy_packs: list[str] = []
    by_pack_records: dict[str, list[TopicTreeRecord]] = defaultdict(list)
    for record in _unique_records([*recent_published, *unique_supply_pool]):
        if record.topic_pack_id:
            by_pack_records[record.topic_pack_id].append(record)
    for pack_id, records in by_pack_records.items():
        unique_communities = {record.community for record in records if record.community}
        if len(unique_communities) < 2 or all(record.is_old_source for record in records if record.community):
            half_healthy_packs.append(pack_id)
    return {
        "decision": "publish",
        "window_days": 7,
        "publish_pack_counts": dict(publish_pack_counts),
        "publish_cluster_counts": dict(publish_cluster_counts),
        "pool_pack_counts": dict(pool_pack_counts),
        "pool_cluster_counts": dict(pool_cluster_counts),
        "blocked_supply_packs": blocked_supply_packs,
        "blocked_supply_clusters": blocked_supply_clusters,
        "missing_supply_packs": supply_gap_packs,
        "half_healthy_packs": sorted(set(half_healthy_packs)),
    }


def build_source_health_under_tree_audit(
    *,
    scope_id: str,
    history_records: list[TopicTreeRecord],
    planned_records: list[TopicTreeRecord],
    candidate_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    del scope_id
    recent_records = _unique_records(
        [
            *window_records(history_records, reference_time=reference_time, days=7),
            *planned_records,
            *candidate_records,
        ]
    )
    by_pack: dict[str, list[TopicTreeRecord]] = defaultdict(list)
    for record in recent_records:
        if record.topic_pack_id:
            by_pack[record.topic_pack_id].append(record)
    pack_health: dict[str, dict[str, Any]] = {}
    risky_packs: list[str] = []
    new_source_credit_count = 0
    for pack_id, records in by_pack.items():
        community_counts = Counter(record.community for record in records if record.community)
        total = sum(community_counts.values())
        top1_share = (community_counts.most_common(1)[0][1] / total) if total and community_counts else 0.0
        top3_share = (sum(value for _, value in community_counts.most_common(3)) / total) if total and community_counts else 0.0
        old_dominance = sum(1 for record in records if record.is_old_source)
        new_source_hits = sum(1 for record in records if record.is_new_source)
        new_source_credit_count += new_source_hits
        unhealthy = total > 0 and (top1_share >= 0.6 or top3_share >= 0.85 or (old_dominance == total and new_source_hits == 0))
        if unhealthy:
            risky_packs.append(pack_id)
        pack_health[pack_id] = {
            "record_count": len(records),
            "unique_source_count": len(community_counts),
            "top1_source_share": round(top1_share, 4),
            "top3_source_share": round(top3_share, 4),
            "new_source_hits": new_source_hits,
            "old_source_hits": old_dominance,
            "decision": "rewrite" if unhealthy else "publish",
        }
    decision = "publish" if not risky_packs else "rewrite"
    return {
        "decision": decision,
        "window_days": 7,
        "pack_health": pack_health,
        "risky_pack_ids": sorted(risky_packs),
        "new_source_credit_count": new_source_credit_count,
    }


def _unique_records(records: list[TopicTreeRecord]) -> list[TopicTreeRecord]:
    by_item_id: dict[str, TopicTreeRecord] = {}
    for record in records:
        by_item_id[record.item_id] = record
    return list(by_item_id.values())


def _record_cluster_ids(record: TopicTreeRecord) -> tuple[str, ...]:
    cluster_ids = tuple(cluster_id for cluster_id in record.topic_cluster_ids if cluster_id)
    if cluster_ids:
        return cluster_ids
    if record.topic_cluster_id:
        return (record.topic_cluster_id,)
    return ()


def rotation_signal_for_record(
    *,
    record: TopicTreeRecord,
    history_records: list[TopicTreeRecord],
    selected_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    recent_3d = [*window_records(history_records, reference_time=reference_time, days=3), *selected_records]
    event_hits = [item for item in recent_3d if item.item_id != record.item_id and item.event_key == record.event_key]
    angle_hits = [item for item in recent_3d if item.item_id != record.item_id and item.angle_key == record.angle_key]
    named_hits = [
        item
        for item in recent_3d
        if item.item_id != record.item_id and set(item.named_topic_ids).intersection(record.named_topic_ids)
    ]
    same_community_recent_count = sum(
        1
        for item in recent_3d
        if item.item_id != record.item_id and item.community and item.community == record.community
    )
    hit_scores = [item.score_hint for item in [*event_hits, *angle_hits, *named_hits]]
    strongest_recent = max(hit_scores) if hit_scores else 0.0
    cooldown_hit = bool(event_hits or angle_hits or named_hits or same_community_recent_count >= 2)
    override = cooldown_hit and record.score_hint >= max(220.0, strongest_recent * 1.15)
    return {
        "same_event_within_3d": bool(event_hits),
        "same_angle_within_3d": bool(angle_hits),
        "named_topic_cooldown_hit": bool(named_hits),
        "same_community_recent_count": same_community_recent_count,
        "cooldown_penalty": cooldown_hit and not override,
        "cooldown_override": override,
    }


def source_health_signal_for_record(
    *,
    record: TopicTreeRecord,
    history_records: list[TopicTreeRecord],
    selected_records: list[TopicTreeRecord],
    reference_time: datetime,
) -> dict[str, Any]:
    recent_7d = [*window_records(history_records, reference_time=reference_time, days=7), *selected_records]
    same_pack = [item for item in recent_7d if item.topic_pack_id and item.topic_pack_id == record.topic_pack_id]
    community_counts = Counter(item.community for item in same_pack if item.community)
    total = sum(community_counts.values())
    top1_source = community_counts.most_common(1)[0][0] if community_counts else None
    top1_share = (community_counts.most_common(1)[0][1] / total) if total and community_counts else 0.0
    top3_share = (
        sum(value for _, value in community_counts.most_common(3)) / total
        if total and community_counts
        else 0.0
    )
    selected_community_penalty = (
        max(Counter(item.community for item in selected_records if item.community).get(record.community, 0) - 1, 0)
        if record.community
        else 0
    )
    relieves_concentration = bool(
        record.community
        and (
            record.is_new_source
            or (top1_source is not None and record.community != top1_source and top1_share >= 0.6)
        )
    )
    return {
        "top1_source": top1_source,
        "top1_source_share": round(top1_share, 4),
        "top3_source_share": round(top3_share, 4),
        "relieves_old_source_concentration": relieves_concentration,
        "dominant_old_source_penalty": bool(
            record.community
            and top1_source is not None
            and record.community == top1_source
            and top1_share >= 0.6
            and not record.is_new_source
        ),
        "selected_community_penalty": selected_community_penalty,
        "is_new_source": record.is_new_source,
    }


__all__ = [
    "build_rolling_rotation_cooldown_audit",
    "build_source_health_under_tree_audit",
    "build_topic_tree_governance_audit",
    "build_tree_coverage_allocation_audit",
    "build_tree_supply_coverage_yield_audit",
    "rotation_signal_for_record",
    "source_health_signal_for_record",
]
