from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.services.hotpost.named_topic_candidate_collector import build_custom_named_topic_watch
from app.services.hotpost.named_topic_watchlist import NamedTopicWatch
from app.services.hotpost.source_scope_catalog import get_scope_topic_packs
from app.services.hotpost.topic_tree_governance_planner import TopicTreeGovernancePlanner
from app.services.hotpost.topic_tree_visible_governance import (
    build_visible_tree_governance_snapshot,
)


def rebalance_publish_list_for_governance(
    *,
    publish_list: list[dict[str, Any]],
    planner_map: dict[str, TopicTreeGovernancePlanner],
    candidate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    current = list(publish_list)
    while True:
        payload = _build_governance_payload(
            planner_map=planner_map,
            publish_list=current,
            candidate_rows=candidate_rows,
        )
        visible_snapshot = build_visible_tree_governance_snapshot(
            items=current,
            candidate_items=candidate_rows,
        )
        flagged_ids = [
            flagged["item_id"]
            for scope_payload in (payload.get("scopes") or {}).values()
            for flagged in list(((scope_payload.get("rotation") or {}).get("flagged_items") or []))
        ]
        flagged_ids.extend(
            _flag_visible_governance_items(
                publish_list=current,
                snapshot=visible_snapshot,
            )
        )
        flagged_ids = list(dict.fromkeys(flagged_ids))
        if not flagged_ids:
            return current
        baseline = _governance_score(
            payload=payload,
            item_count=len(current),
            visible_snapshot=visible_snapshot,
            candidate_rows=candidate_rows,
        )
        current_keys = {str(item.get("plan_key") or "") for item in current}
        candidate_pool = [
            item
            for item in candidate_rows
            if str(item.get("plan_key") or "") not in current_keys
        ]
        improved: list[dict[str, Any]] | None = None
        improved_score: tuple[Any, ...] | None = None
        for item_id in flagged_ids:
            flagged_index = next(
                (
                    index
                    for index, item in enumerate(current)
                    if str(item.get("plan_key") or "") == item_id
                ),
                None,
            )
            if flagged_index is None:
                continue
            for replacement in candidate_pool:
                if str(replacement.get("lane") or "") != str(current[flagged_index].get("lane") or ""):
                    continue
                trial = list(current)
                trial[flagged_index] = replacement
                trial_payload = _build_governance_payload(
                    planner_map=planner_map,
                    publish_list=trial,
                    candidate_rows=candidate_rows,
                )
                trial_visible_snapshot = build_visible_tree_governance_snapshot(
                    items=trial,
                    candidate_items=candidate_rows,
                )
                trial_score = _governance_score(
                    payload=trial_payload,
                    item_count=len(trial),
                    visible_snapshot=trial_visible_snapshot,
                    candidate_rows=candidate_rows,
                )
                if trial_score < baseline and (improved_score is None or trial_score < improved_score):
                    improved = trial
                    improved_score = trial_score
        if improved is None:
            return current
        current = improved


def build_governance_topic_watches(
    *,
    plan_payload: dict[str, Any],
    gate_summary: dict[str, Any],
    scope_id: str,
) -> list[NamedTopicWatch]:
    governance = ((gate_summary.get("topic_tree_governance") or {}).get("scopes") or {}).get(scope_id) or {}
    if not governance or str(governance.get("overall_decision") or "publish") == "publish":
        return []
    publish_list = list(plan_payload.get("publish_list") or [])
    items_by_key = {
        str(item.get("plan_key") or ""): item
        for item in publish_list
        if str(item.get("plan_key") or "").strip()
    }
    requests: dict[str, dict[str, Any]] = defaultdict(lambda: {"reasons": set(), "excluded": set(), "cluster_ids": set()})

    for flagged in list(((governance.get("rotation") or {}).get("flagged_items") or [])):
        item = items_by_key.get(str(flagged.get("item_id") or ""))
        if not item:
            continue
        pack_id = str(item.get("topic_pack_id") or "").strip()
        if not pack_id:
            continue
        request = requests[pack_id]
        request["reasons"].add("rotation")
        request["excluded"].update(_item_communities(item))
        request["cluster_ids"].update(_item_cluster_ids(item))

    risky_pack_ids = list(((governance.get("source_health") or {}).get("risky_pack_ids") or []))
    for pack_id in risky_pack_ids:
        normalized_pack_id = str(pack_id or "").strip()
        if not normalized_pack_id:
            continue
        request = requests[normalized_pack_id]
        request["reasons"].add("source_health")
        for item in publish_list:
            if str(item.get("topic_pack_id") or "").strip() != normalized_pack_id:
                continue
            request["excluded"].update(_item_communities(item))
            request["cluster_ids"].update(_item_cluster_ids(item))

    watches: list[NamedTopicWatch] = []
    for pack in get_scope_topic_packs(scope_id):
        if pack.topic_pack_id not in requests:
            continue
        request = requests[pack.topic_pack_id]
        all_subreddits = [str(item).strip().replace("r/", "") for item in list(pack.subreddits or []) if str(item).strip()]
        if not all_subreddits:
            continue
        excluded = {str(item).lower() for item in request["excluded"]}
        candidate_subreddits = [item for item in all_subreddits if item.lower() not in excluded]
        if not candidate_subreddits:
            candidate_subreddits = all_subreddits
        queries = [str(item).strip() for item in list(pack.search_queries or []) if str(item).strip()]
        if not queries:
            continue
        reasons = sorted(str(item) for item in request["reasons"])
        has_rotation = "rotation" in reasons
        has_source_health = "source_health" in reasons
        if has_rotation and has_source_health:
            candidate_cap = 2
        elif has_rotation:
            candidate_cap = 1
        elif has_source_health:
            candidate_cap = 6
        else:
            candidate_cap = 4
        watches.append(
            build_custom_named_topic_watch(
                topic_id=f"governance-{pack.topic_pack_id}-{'-'.join(reasons)}",
                scope_id=scope_id,
                topic_pack_id=pack.topic_pack_id,
                topic_cluster_ids=(
                    None
                    if has_rotation
                    else sorted(str(item) for item in request["cluster_ids"] if str(item).strip()) or None
                ),
                queries=queries[: max(3, min(len(queries), 6))],
                subreddits=candidate_subreddits,
                time_filter="day" if has_rotation else "week",
                candidate_cap=candidate_cap,
            )
        )
    return watches


def build_governance_topic_watches_for_gate(
    *,
    plan_payload: dict[str, Any],
    gate_summary: dict[str, Any],
    scope_id: str | None,
) -> list[NamedTopicWatch]:
    if scope_id is not None:
        return build_governance_topic_watches(
            plan_payload=plan_payload,
            gate_summary=gate_summary,
            scope_id=scope_id,
        )

    governance_scopes = ((gate_summary.get("topic_tree_governance") or {}).get("scopes") or {})
    watches: list[NamedTopicWatch] = []
    seen: set[tuple[str, str, str]] = set()
    for resolved_scope_id, governance in governance_scopes.items():
        if str((governance or {}).get("overall_decision") or "publish") == "publish":
            continue
        for watch in build_governance_topic_watches(
            plan_payload=plan_payload,
            gate_summary=gate_summary,
            scope_id=str(resolved_scope_id),
        ):
            dedupe_key = (watch.scope_id, watch.topic_pack_id, watch.topic_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            watches.append(watch)
    return watches


def _build_governance_payload(
    *,
    planner_map: dict[str, TopicTreeGovernancePlanner],
    publish_list: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    scope_payload = {
        scope_id: planner.build_audit(plan_items=publish_list, candidate_items=candidate_rows)
        for scope_id, planner in planner_map.items()
    }
    overall_decision = "publish"
    decisions = [payload["overall_decision"] for payload in scope_payload.values()]
    if "fail" in decisions:
        overall_decision = "fail"
    elif "rewrite" in decisions:
        overall_decision = "rewrite"
    return {
        "overall_decision": overall_decision,
        "scopes": scope_payload,
        "visible_projection": build_visible_tree_governance_snapshot(
            items=publish_list,
            candidate_items=candidate_rows,
        ),
    }


def _governance_score(
    *,
    payload: dict[str, Any],
    item_count: int,
    visible_snapshot: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
) -> tuple[Any, ...]:
    decisions = {"publish": 0, "rewrite": 1, "fail": 2}
    scope_payloads = list((payload.get("scopes") or {}).values())
    rotation_flagged = sum(len(list(((scope.get("rotation") or {}).get("flagged_items") or []))) for scope in scope_payloads)
    risky_packs = sum(len(list(((scope.get("source_health") or {}).get("risky_pack_ids") or []))) for scope in scope_payloads)
    missing_packs = sum(len(list(((scope.get("allocation") or {}).get("missing_pack_ids") or []))) for scope in scope_payloads)
    missing_supply = sum(len(list(((scope.get("supply") or {}).get("missing_supply_packs") or []))) for scope in scope_payloads)
    return (
        decisions.get(str(payload.get("overall_decision") or "publish"), 3),
        rotation_flagged,
        risky_packs,
        missing_packs,
        missing_supply,
        len(list(visible_snapshot.get("missing_scope_ids") or [])),
        len(list(visible_snapshot.get("overweight_communities") or [])),
        len(list(visible_snapshot.get("overweight_pack_ids") or [])),
        len(list(visible_snapshot.get("overweight_scope_ids") or [])),
        -int(visible_snapshot.get("new_source_count") or 0),
        float(visible_snapshot.get("top_community_share") or 0.0),
        float(visible_snapshot.get("top_pack_share") or 0.0),
        float(visible_snapshot.get("top_scope_share") or 0.0),
        -item_count,
    )


def _flag_visible_governance_items(
    *,
    publish_list: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> list[str]:
    overweight_communities = {str(item) for item in list(snapshot.get("overweight_communities") or [])}
    overweight_pack_ids = {str(item) for item in list(snapshot.get("overweight_pack_ids") or [])}
    overweight_scope_ids = {str(item) for item in list(snapshot.get("overweight_scope_ids") or [])}
    missing_scope_ids = {str(item) for item in list(snapshot.get("missing_scope_ids") or [])}
    if not (overweight_communities or overweight_pack_ids or overweight_scope_ids or missing_scope_ids):
        return []

    flagged: list[str] = []
    current_scope_counts = defaultdict(int)
    for item in publish_list:
        current_scope_counts[str(item.get("source_scope_id") or "")] += 1

    overrepresented_scope_ids = set(overweight_scope_ids)
    if missing_scope_ids and current_scope_counts:
        max_count = max(current_scope_counts.values())
        overrepresented_scope_ids.update(
            scope_id for scope_id, count in current_scope_counts.items() if count == max_count
        )

    for item in publish_list:
        community = (
            str(item.get("top_community") or "")
            .replace("r/", "")
            .strip()
            .lower()
        )
        pack_id = str(item.get("topic_pack_id") or "").strip()
        scope_id = str(item.get("source_scope_id") or "").strip()
        if community and community in overweight_communities:
            flagged.append(str(item.get("plan_key") or ""))
            continue
        if pack_id and pack_id in overweight_pack_ids:
            flagged.append(str(item.get("plan_key") or ""))
            continue
        if scope_id and scope_id in overrepresented_scope_ids:
            flagged.append(str(item.get("plan_key") or ""))
    return [item_id for item_id in flagged if item_id]


def _item_communities(item: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    subreddit = str(item.get("matched_subreddit") or "").strip().replace("r/", "")
    if subreddit:
        values.add(subreddit.lower())
    for raw in list(item.get("source_communities") or []):
        community = str(raw or "").strip().replace("r/", "")
        if community:
            values.add(community.lower())
    return values


def _item_cluster_ids(item: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    cluster_id = str(item.get("topic_cluster_id") or "").strip()
    if cluster_id:
        values.add(cluster_id)
    for raw in list(item.get("topic_cluster_ids") or []):
        cluster = str(raw or "").strip()
        if cluster:
            values.add(cluster)
    return values


__all__ = [
    "build_governance_topic_watches",
    "build_governance_topic_watches_for_gate",
    "rebalance_publish_list_for_governance",
]
