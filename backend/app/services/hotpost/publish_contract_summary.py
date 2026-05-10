from __future__ import annotations

from pathlib import Path
from typing import Any
import json


PRIORITY_PACK_IDS = (
    "upstream-winds",
    "tools-efficiency",
    "funnel-conversion",
    "category-winds",
)

PRIORITY_CLUSTER_IDS = (
    "key-people-and-route",
    "ai-product-and-adoption",
    "platform-policy-shifts",
    "small-goods",
)

TREND_AUDIT_PATH = (
    Path(__file__).resolve().parents[4]
    / "reports"
    / "evals"
    / "mini-release-trend-audit-latest.json"
)


def build_publish_contract_summary(
    *,
    inventory_summary: dict[str, Any],
    publish_list: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    governance_pool_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    trend_summary = _load_latest_trend_summary()
    thin_packs = _priority_pack_counts(candidate_rows)
    blank_clusters = _blank_priority_clusters(governance_pool_rows)
    publish_pack_counts = _priority_pack_counts(publish_list)
    conversion = _conversion_metrics(inventory_summary)
    achieved = _achieved_flags(
        inventory_summary=inventory_summary,
        trend_summary=trend_summary,
    )
    gaps = _current_gaps(
        inventory_summary=inventory_summary,
        thin_packs=thin_packs,
        blank_clusters=blank_clusters,
        trend_summary=trend_summary,
    )
    priorities = _next_priorities(
        thin_packs=thin_packs,
        blank_clusters=blank_clusters,
        trend_summary=trend_summary,
    )

    return {
        "version": "unified-contract-v1",
        "overall_goal": (
            "系统能稳定、持续地从整棵题材树里挖出真正够硬的信息，"
            "用健康来源和不疲劳的轮换方式出卡。"
        ),
        "desired_effects": {
            "all_scope_tree_visible": True,
            "only_publish_hard_cards": True,
            "topic_tree_not_eaten_by_strong_packs": True,
            "source_health_not_old_community_locked": True,
            "multi_day_rotation_without_fatigue": True,
            "stable_workflow_not_manual_judgment": True,
        },
        "achieved": achieved,
        "not_yet_reached": gaps,
        "priority_next_steps": priorities,
        "current_metrics": {
            "publish_surface_conversion": conversion,
            "priority_pack_supply": thin_packs,
            "priority_pack_in_publish_list": publish_pack_counts,
            "blank_priority_clusters": blank_clusters,
            "latest_trend_status": trend_summary,
        },
    }


def _load_latest_trend_summary() -> dict[str, Any] | None:
    if not TREND_AUDIT_PATH.exists():
        return None
    payload = json.loads(TREND_AUDIT_PATH.read_text(encoding="utf-8"))
    latest = next(iter(payload.get("release_summaries") or []), None)
    if not latest:
        return None
    return {
        "latest_release_id": payload.get("latest_release_id"),
        "latest_status": payload.get("latest_status"),
        "stable_streak": int(payload.get("stable_streak") or 0),
        "remaining_new_releases": int(payload.get("remaining_new_releases") or 0),
        "front30_alerts": list((latest.get("front30") or {}).get("alerts") or []),
        "full_inventory_alerts": list((latest.get("full") or {}).get("alerts") or []),
        "watched_communities": dict((latest.get("full") or {}).get("watched_communities") or {}),
        "watched_packs": dict((latest.get("full") or {}).get("watched_packs") or {}),
    }


def _priority_pack_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        pack_id: 0
        for pack_id in PRIORITY_PACK_IDS
    }
    for row in rows:
        pack_id = str(row.get("topic_pack_id") or "")
        if pack_id in counts:
            counts[pack_id] += 1
    return counts


def _blank_priority_clusters(rows: list[dict[str, Any]]) -> list[str]:
    present: set[str] = set()
    for row in rows:
        cluster_id = str(row.get("topic_cluster_id") or "").strip()
        if cluster_id:
            present.add(cluster_id)
        for item in list(row.get("topic_cluster_ids") or []):
            normalized = str(item).strip()
            if normalized:
                present.add(normalized)
    return [cluster_id for cluster_id in PRIORITY_CLUSTER_IDS if cluster_id not in present]


def _conversion_metrics(inventory_summary: dict[str, Any]) -> dict[str, Any]:
    candidate_count = int(inventory_summary.get("candidate_count") or 0)
    publish_surface_count = int(inventory_summary.get("candidate_publish_surface_count") or 0)
    weak_candidate_count = int(inventory_summary.get("weak_candidate_count") or 0)
    return {
        "candidate_count": candidate_count,
        "publish_surface_count": publish_surface_count,
        "weak_candidate_count": weak_candidate_count,
        "surface_rate": round(publish_surface_count / candidate_count, 3) if candidate_count else 0.0,
        "weak_rate": round(weak_candidate_count / candidate_count, 3) if candidate_count else 0.0,
    }


def _achieved_flags(
    *,
    inventory_summary: dict[str, Any],
    trend_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "rules_layer_established": True,
        "all_scope_default": True,
        "visible_layer_improved": bool(trend_summary and not trend_summary.get("front30_alerts")),
        "rolling_inventory_governed": bool(trend_summary),
        "stability_chain_defaulted": bool(trend_summary),
        "weak_items_filtered_early": int(inventory_summary.get("weak_candidate_count") or 0) > 0,
    }


def _current_gaps(
    *,
    inventory_summary: dict[str, Any],
    thin_packs: dict[str, int],
    blank_clusters: list[str],
    trend_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    watched_communities = dict((trend_summary or {}).get("watched_communities") or {})
    watched_packs = dict((trend_summary or {}).get("watched_packs") or {})
    return {
        "supply_thickness_not_enough": {
            "status": int(inventory_summary.get("candidate_publish_surface_count") or 0) <= 8,
            "reason": "当前真正能进发布面的 fresh hard info 仍偏薄。",
        },
        "thin_priority_packs": {
            pack_id: count
            for pack_id, count in thin_packs.items()
            if count <= 3
        },
        "blank_priority_clusters": blank_clusters,
        "source_health_not_yet_structural": {
            "status": bool(
                watched_communities
                and max(watched_communities.values(), default=0) >= 5
                or watched_packs
                and max(watched_packs.values(), default=0) >= 14
            ),
            "reason": "当前是已压稳，不代表已经自然健康。",
        },
        "publish_until_exhausted_is_sop_not_orchestrator": True,
    }


def _next_priorities(
    *,
    thin_packs: dict[str, int],
    blank_clusters: list[str],
    trend_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "focus": "thicken_supply_without_breaking_stable",
        "thin_packs_first": [
            pack_id
            for pack_id, count in thin_packs.items()
            if count <= 3
        ],
        "blank_clusters_first": list(blank_clusters),
        "keep_stable_watch": {
            "latest_status": (trend_summary or {}).get("latest_status"),
            "watched_communities": dict((trend_summary or {}).get("watched_communities") or {}),
            "watched_packs": dict((trend_summary or {}).get("watched_packs") or {}),
        },
    }
