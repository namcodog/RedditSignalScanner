from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.services.hotpost.breakdown_candidate_clusterer import list_breakdown_suggestions
from app.services.hotpost.card_candidate_store import list_candidates
from app.services.hotpost.card_draft_builder import build_published_card
from app.services.hotpost.card_draft_store import list_drafts
from app.services.hotpost.card_lane_policy import infer_validation_lane
from app.services.hotpost.card_payload_store import load_published_cards
from app.services.hotpost.card_selection_policy import prioritize_validate_candidates
from app.services.hotpost.draft_surface_readiness import is_draft_surface_ready
from app.services.hotpost.hotpost_supply_contract import get_supply_operation_defaults, resolve_supply_lane_targets
from app.services.hotpost.publish_surface_quality import assess_publish_surface_candidate
from app.services.hotpost.publish_contract_summary import build_publish_contract_summary
from app.services.hotpost.topic_metadata import resolve_topic_metadata
from app.services.hotpost.topic_tree_governance_planner import TopicTreeGovernancePlanner
from app.services.hotpost.topic_tree_publish_surface_planner import TopicTreePublishSurfacePlanner
from app.services.hotpost.topic_tree_governance_remediation import rebalance_publish_list_for_governance

_NAMED_TOPIC_BUDGET = {
    "max_named_topic_cards": 3,
    "single_named_topic_max": 1,
}
_SIGNAL_TARGET_WINDOW_HOURS = 72.0


def build_offline_publish_plan(
    *,
    limit:Optional[ int] = None,
    breakdown_suggestion_limit: int = 30,
    scope: str | None = None,
) -> dict[str, Any]:
    reference_time = datetime.now(timezone.utc)
    published_items = load_published_cards()
    if scope is not None:
        published_items = [item for item in published_items if str(item.get("source_scope_id") or "") == scope]
    operation_defaults = get_supply_operation_defaults()
    target_total = int(limit or operation_defaults["min_cards_per_run"])
    lane_targets = resolve_supply_lane_targets(target_total)

    drafts = list_drafts(scope)
    published_card_ids = {str(item.get("card_id") or "") for item in published_items}
    ready_validate_drafts, ready_write_drafts, surface_ready_drafts = _ready_drafts(drafts)
    reserved_candidate_ids = {
        candidate_id
        for draft in surface_ready_drafts
        for candidate_id in list(getattr(draft, "candidate_ids", []) or [])
    }
    reserved_candidate_ids.update(str(getattr(draft, "candidate_id", "") or "") for draft in surface_ready_drafts)

    ranked_candidates = prioritize_validate_candidates(list_candidates(scope), published_items=published_items)
    weak_candidate_count = 0
    candidate_rows: list[dict[str, Any]] = []
    for candidate in ranked_candidates:
        if candidate.candidate_id in reserved_candidate_ids:
            continue
        if f"card-{candidate.candidate_id}-validate" in published_card_ids:
            continue
        if f"card-{candidate.candidate_id}-write" in published_card_ids:
            continue
        if _is_governance_named_topic_candidate(candidate):
            continue
        row = _candidate_row(candidate)
        if row is None:
            weak_candidate_count += 1
            continue
        candidate_rows.append(row)

    breakdown_suggestions = list_breakdown_suggestions(scope, limit=breakdown_suggestion_limit)
    signal_draft_rows = _draft_rows(ready_validate_drafts, lane="signal")
    hot_draft_rows = _draft_rows(ready_validate_drafts, lane="hot")
    write_draft_rows = _write_draft_rows(ready_write_drafts)
    governance_pool_rows = [
        *candidate_rows,
        *signal_draft_rows,
        *hot_draft_rows,
        *write_draft_rows,
    ]

    lane_pools: dict[str, list[dict[str, Any]]] = {
        "signal": [*signal_draft_rows, *[row for row in candidate_rows if row["lane"] == "signal"]],
        "hot": [*hot_draft_rows, *[row for row in candidate_rows if row["lane"] == "hot"]],
        "breakdown": [*write_draft_rows],
    }

    publish_list: list[dict[str, Any]] = []
    lane_counts: Counter[str] = Counter()
    named_topic_counts: Counter[str] = Counter()
    used_keys: set[str] = set()
    planner_map = _build_governance_planners(
        published_items=published_items,
        candidate_rows=governance_pool_rows,
        reference_time=reference_time,
    )
    publish_surface_planner = TopicTreePublishSurfacePlanner(
        history_items=published_items,
        candidate_items=governance_pool_rows,
        reference_time=reference_time,
    )
    lane_order = _lane_selection_order(target_total)
    for lane in lane_order:
        publish_list.extend(
            _take_from_pool(
                lane_pools[lane],
                need=lane_targets.get(lane, 0),
                target_total=target_total,
                lane_counts=lane_counts,
                lane_targets=lane_targets,
                named_topic_counts=named_topic_counts,
                used_keys=used_keys,
                planner_map=planner_map,
                publish_surface_planner=publish_surface_planner,
            )
        )
    remainder: list[dict[str, Any]] = []
    for lane in lane_order:
        remainder.extend(item for item in lane_pools[lane] if item["plan_key"] not in used_keys)
    remainder.sort(
        key=lambda item: _plan_sort_key(
            item,
            lane_counts=lane_counts,
            lane_targets=lane_targets,
            planner_map=planner_map,
            publish_surface_planner=publish_surface_planner,
        )
    )
    for item in remainder:
        if len(publish_list) >= target_total:
            break
        if not _can_take_named_topic(item, named_topic_counts=named_topic_counts):
            continue
        publish_list.append(item)
        used_keys.add(item["plan_key"])
        _apply_selection(
            item,
            lane_counts=lane_counts,
            named_topic_counts=named_topic_counts,
            planner_map=planner_map,
            publish_surface_planner=publish_surface_planner,
        )

    publish_list = _apply_growth_purity_cleanup(
        publish_list=publish_list[:target_total],
        candidate_rows=candidate_rows,
    )
    publish_list = rebalance_publish_list_for_governance(
        publish_list=publish_list,
        planner_map=planner_map,
        candidate_rows=governance_pool_rows,
    )
    final_publish_list = _repair_signal_target_freshness(
        publish_list=publish_list[:target_total],
        candidate_rows=candidate_rows,
        reference_time=reference_time,
    )

    inventory_summary = {
        "published_count": len(published_items),
        "draft_count": len(drafts),
        "ready_validate_drafts": len(ready_validate_drafts),
        "ready_write_drafts": len(ready_write_drafts),
        "candidate_count": len(ranked_candidates),
        "candidate_publish_surface_count": len(candidate_rows),
        "weak_candidate_count": weak_candidate_count,
        "breakdown_suggestion_count": len(breakdown_suggestions),
    }

    return {
        "generated_at": _utc_iso(),
        "targets": {
            "total": target_total,
            "lane_targets": lane_targets,
        },
        "scope": scope,
        "inventory_summary": inventory_summary,
        "publish_list": final_publish_list,
        "topic_tree_governance": _build_governance_payload(
            planner_map=planner_map,
            publish_list=final_publish_list,
            candidate_rows=governance_pool_rows,
        ),
        "publish_contract_summary": build_publish_contract_summary(
            inventory_summary=inventory_summary,
            publish_list=final_publish_list,
            candidate_rows=candidate_rows,
            governance_pool_rows=governance_pool_rows,
        ),
    }


def _ready_drafts(
    drafts: list[ValidationCardDraft | WritingCardDraft],
) -> tuple[list[ValidationCardDraft], list[WritingCardDraft], list[ValidationCardDraft | WritingCardDraft]]:
    ready_validate: list[ValidationCardDraft] = []
    ready_write: list[WritingCardDraft] = []
    surface_ready: list[ValidationCardDraft | WritingCardDraft] = []
    for draft in drafts:
        if not is_draft_surface_ready(draft):
            continue
        surface_ready.append(draft)
        try:
            build_published_card(draft)
        except Exception:
            continue
        if draft.card_type == "validate":
            ready_validate.append(draft)
        else:
            ready_write.append(draft)
    return ready_validate, ready_write, surface_ready


def _candidate_row(candidate: CandidatePack) -> dict[str, Any] | None:
    metadata = resolve_topic_metadata(candidate.model_dump(mode="json"))
    lane = infer_validation_lane(candidate)
    quality = assess_publish_surface_candidate(candidate, lane=lane)
    if quality["should_block"]:
        return None
    return {
        "plan_key": f"candidate:{candidate.candidate_id}",
        "source_type": "candidate",
        "lane": lane,
        "card_type": "validate",
        "candidate_id": candidate.candidate_id,
        "card_id": f"card-{candidate.candidate_id}-validate",
        "title": candidate.title,
        "source_scope_id": candidate.source_scope_id,
        "score_hint": float(candidate.score) + float(candidate.num_comments) / 10.0,
        "matched_subreddit": candidate.matched_subreddit,
        "source_communities": list(candidate.top_communities or []),
        "primary_reason": candidate.primary_reason,
        "publish_surface_tier": quality.get("tier"),
        "quality_reasons": list(quality["reasons"]),
        "quality_base_reasons": list(quality.get("base_reasons") or []),
        "quality_relaxed_reasons": list(quality.get("relaxed_reasons") or []),
        "source_event_at": candidate.created_at.isoformat().replace("+00:00", "Z"),
        **metadata,
    }


def _is_governance_named_topic_candidate(candidate: CandidatePack) -> bool:
    named_topic_ids = list(getattr(candidate, "named_topic_ids", []) or [])
    return any(str(topic_id).startswith("governance-") for topic_id in named_topic_ids)


def _draft_rows(drafts: list[ValidationCardDraft], *, lane: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for draft in drafts:
        if draft.lane != lane:
            continue
        metadata = resolve_topic_metadata(draft.model_dump(mode="json"))
        rows.append(
            {
                "plan_key": f"draft:{draft.draft_id}",
                "source_type": "draft",
                "lane": draft.lane,
                "card_type": draft.card_type,
                "draft_id": draft.draft_id,
                "candidate_id": draft.candidate_id,
                "card_id": draft.card_id,
                "title": draft.title,
                "source_scope_id": draft.source_scope_id,
                "score_hint": float(draft.score) + float(draft.num_comments) / 10.0 + 200.0,
                "source_event_at": draft.source_event_at.isoformat().replace("+00:00", "Z"),
                **metadata,
            }
        )
    return rows


def _write_draft_rows(drafts: list[WritingCardDraft]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for draft in drafts:
        metadata = resolve_topic_metadata(draft.model_dump(mode="json"))
        rows.append(
            {
                "plan_key": f"draft:{draft.draft_id}",
                "source_type": "draft",
                "lane": "breakdown",
                "card_type": draft.card_type,
                "draft_id": draft.draft_id,
                "candidate_id": draft.candidate_id,
                "card_id": draft.card_id,
                "title": draft.title,
                "source_scope_id": draft.source_scope_id,
                "score_hint": float(draft.thread_count) * 20.0 + float(draft.community_count) * 12.0 + 220.0,
                "source_event_at": draft.source_event_at.isoformat().replace("+00:00", "Z"),
                **metadata,
            }
        )
    return rows
def _take_from_pool(
    pool: list[dict[str, Any]],
    *,
    need: int,
    target_total: int,
    lane_counts: Counter[str],
    lane_targets: dict[str, int],
    named_topic_counts: Counter[str],
    used_keys: set[str],
    planner_map: dict[str, TopicTreeGovernancePlanner],
    publish_surface_planner: TopicTreePublishSurfacePlanner | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    available = [item for item in pool if item["plan_key"] not in used_keys]
    lane = str(pool[0]["lane"]) if pool else ""
    while len(selected) < need and available:
        eligible = [item for item in available if _can_take_named_topic(item, named_topic_counts=named_topic_counts)]
        if not eligible:
            break
        working = eligible
        if lane == "breakdown" and target_total <= 15:
            selected_pack_keys = {f"{item['source_scope_id']}:{item.get('topic_pack_id') or 'unknown'}" for item in selected}
            unseen_pack_items = [
                item
                for item in working
                if f"{item['source_scope_id']}:{item.get('topic_pack_id') or 'unknown'}" not in selected_pack_keys
            ]
            if unseen_pack_items:
                working = unseen_pack_items
        working.sort(
            key=lambda item: _plan_sort_key(
                item,
                lane_counts=lane_counts,
                lane_targets=lane_targets,
                planner_map=planner_map,
                publish_surface_planner=publish_surface_planner,
            )
        )
        chosen = working.pop(0)
        selected.append(chosen)
        used_keys.add(chosen["plan_key"])
        _apply_selection(
            chosen,
            lane_counts=lane_counts,
            named_topic_counts=named_topic_counts,
            planner_map=planner_map,
            publish_surface_planner=publish_surface_planner,
        )
        available = [item for item in available if item["plan_key"] not in used_keys]
    return selected


def _plan_sort_key(
    item: dict[str, Any],
    *,
    lane_counts: Counter[str],
    lane_targets: dict[str, int],
    planner_map: dict[str, TopicTreeGovernancePlanner],
    publish_surface_planner: TopicTreePublishSurfacePlanner | None = None,
) -> tuple[Any, ...]:
    hot_source_rank = 0 if item.get("lane") == "hot" and item.get("source_type") == "draft" else 1
    scope_id = str(item.get("source_scope_id") or "")
    publish_surface_key: tuple[Any, ...] = ()
    if publish_surface_planner is not None:
        publish_surface_key = publish_surface_planner.sort_key(
            item,
            lane_counts=lane_counts,
            lane_targets=lane_targets,
        )
    planner = planner_map.get(scope_id)
    if planner is None:
        lane_gap = int(lane_targets.get(str(item.get("lane") or ""), 0)) - int(lane_counts.get(str(item.get("lane") or ""), 0))
        return (
            hot_source_rank,
            *publish_surface_key,
            0 if lane_gap > 0 else 1,
            -max(lane_gap, 0),
            -float(item["score_hint"]),
            item["title"],
        )
    planner_key = planner.sort_key(item, lane_counts=lane_counts, lane_targets=lane_targets)
    return (hot_source_rank, *publish_surface_key, *planner_key)


def _apply_selection(
    item: dict[str, Any],
    *,
    lane_counts: Counter[str],
    named_topic_counts: Counter[str],
    planner_map: dict[str, TopicTreeGovernancePlanner],
    publish_surface_planner: TopicTreePublishSurfacePlanner | None = None,
) -> None:
    lane_counts[str(item.get("lane") or "")] += 1
    for topic_id in item.get("named_topic_ids", []) or []:
        named_topic_counts[topic_id] += 1
    planner = planner_map.get(str(item.get("source_scope_id") or ""))
    if planner is not None:
        planner.record_selection(item)
    if publish_surface_planner is not None:
        publish_surface_planner.record_selection(item)


def _can_take_named_topic(
    item: dict[str, Any],
    *,
    named_topic_counts: Counter[str],
) -> bool:
    topic_ids = list(item.get("named_topic_ids", []) or [])
    if not topic_ids:
        return True
    current_total = sum(named_topic_counts.values())
    if current_total >= int(_NAMED_TOPIC_BUDGET["max_named_topic_cards"]):
        return False
    single_max = int(_NAMED_TOPIC_BUDGET["single_named_topic_max"])
    return all(int(named_topic_counts.get(topic_id, 0)) < single_max for topic_id in topic_ids)


def _resolve_lane_targets(target_total: int, configured: dict[str, int]) -> dict[str, int]:
    targets = {str(key): int(value) for key, value in configured.items()}
    return _resolve_scaled_targets(
        target_total,
        targets,
        tie_order=("signal", "hot", "breakdown"),
        overflow_prefers_smaller_targets=False,
    )


def _lane_selection_order(target_total: int) -> tuple[str, ...]:
    if target_total <= 18:
        return ("hot", "signal", "breakdown")
    return ("hot", "breakdown", "signal")


def _resolve_scaled_targets(
    target_total: int,
    configured: dict[str, int],
    *,
    tie_order: tuple[str, ...],
    overflow_prefers_smaller_targets: bool,
) -> dict[str, int]:
    total = sum(configured.values())
    if target_total <= 0:
        return {key: 0 for key in configured}
    if total == target_total:
        return dict(configured)
    if total <= 0:
        first = tie_order[0] if tie_order else next(iter(configured), "signal")
        return {key: (target_total if key == first else 0) for key in configured}

    keys = list(configured.keys())
    order_rank = {name: index for index, name in enumerate(tie_order)}
    scaled = {
        key: (Decimal(target_total) * Decimal(configured[key])) / Decimal(total)
        for key in keys
    }
    adjusted = {
        key: int(scaled[key].quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        for key in keys
    }
    current_total = sum(adjusted.values())
    if current_total > target_total:
        overflow = current_total - target_total
        shrink_order = sorted(
            keys,
            key=lambda key: (
                -adjusted[key],
                configured[key] if overflow_prefers_smaller_targets else -configured[key],
                order_rank.get(key, 99),
            ),
        )
        while overflow > 0:
            moved = False
            for key in shrink_order:
                if adjusted[key] <= 0:
                    continue
                adjusted[key] -= 1
                overflow -= 1
                moved = True
                if overflow <= 0:
                    break
            if not moved:
                break
    elif current_total < target_total:
        deficit = target_total - current_total
        grow_order = sorted(
            keys,
            key=lambda key: (
                -(scaled[key] - Decimal(adjusted[key])),
                -configured[key],
                order_rank.get(key, 99),
            ),
        )
        while deficit > 0:
            for key in grow_order:
                adjusted[key] += 1
                deficit -= 1
                if deficit <= 0:
                    break
    return adjusted


def _lane_rank(lane: str) -> int:
    order = {"signal": 0, "hot": 1, "breakdown": 2}
    return order.get(lane, 99)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_governance_planners(
    *,
    published_items: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    reference_time: datetime,
) -> dict[str, TopicTreeGovernancePlanner]:
    scope_ids = sorted(
        {
            str(item.get("source_scope_id") or "").strip()
            for item in [*published_items, *candidate_rows]
            if str(item.get("source_scope_id") or "").strip()
        }
    )
    return {
        scope_id: TopicTreeGovernancePlanner(
            scope_id=scope_id,
            history_items=published_items,
            candidate_items=candidate_rows,
            reference_time=reference_time,
        )
        for scope_id in scope_ids
    }


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
    }


def _apply_growth_purity_cleanup(
    *,
    publish_list: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    stale_index = next(
        (
            index
            for index, item in enumerate(publish_list)
            if _is_stale_growth_organic_breakdown(item)
        ),
        None,
    )
    if stale_index is None:
        return publish_list

    selected_keys = {str(item.get("plan_key") or "") for item in publish_list}
    replacements = [
        item
        for item in candidate_rows
        if str(item.get("plan_key") or "") not in selected_keys
        and _is_growth_organic_content_marketing_candidate(item)
    ]
    if not replacements:
        return publish_list

    replacements.sort(key=lambda item: (-float(item.get("score_hint") or 0.0), str(item.get("title") or "")))
    updated = list(publish_list)
    updated[stale_index] = replacements[0]
    return updated


def _is_stale_growth_organic_breakdown(item: dict[str, Any]) -> bool:
    return (
        str(item.get("source_scope_id") or "") == "business-growth-ops"
        and str(item.get("topic_pack_id") or "") == "organic-discovery"
        and str(item.get("source_type") or "") == "draft"
        and str(item.get("lane") or "") == "breakdown"
        and str(item.get("candidate_id") or "").startswith("group-business-growth-ops-")
    )


def _is_growth_organic_content_marketing_candidate(item: dict[str, Any]) -> bool:
    return (
        str(item.get("source_scope_id") or "") == "business-growth-ops"
        and str(item.get("topic_pack_id") or "") == "organic-discovery"
        and str(item.get("source_type") or "") == "candidate"
        and str(item.get("primary_reason") or "") == "organic-discovery:listing_keyword_bridge"
        and str(item.get("matched_subreddit") or "") == "content_marketing"
    )


def _repair_signal_target_freshness(
    *,
    publish_list: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    reference_time: datetime,
) -> list[dict[str, Any]]:
    signal_indexes = [index for index, item in enumerate(publish_list) if str(item.get("lane") or "") == "signal"]
    if not signal_indexes:
        return publish_list

    needed_fresh_count = (len(signal_indexes) // 2) + 1
    fresh_count = sum(1 for index in signal_indexes if _is_signal_target_fresh(publish_list[index], reference_time))
    if fresh_count >= needed_fresh_count:
        return publish_list

    selected_keys = {str(item.get("plan_key") or "") for item in publish_list}
    replacements = [
        item
        for item in candidate_rows
        if str(item.get("plan_key") or "") not in selected_keys
        and str(item.get("lane") or "") == "signal"
        and _is_signal_target_fresh(item, reference_time)
    ]
    if not replacements:
        return publish_list

    replacements.sort(key=lambda item: (-float(item.get("score_hint") or 0.0), str(item.get("title") or "")))
    stale_signal_indexes = [
        index
        for index in signal_indexes
        if not _is_signal_target_fresh(publish_list[index], reference_time)
    ]
    stale_signal_indexes.sort(
        key=lambda index: _age_hours(publish_list[index], reference_time) or float("inf"),
        reverse=True,
    )

    updated = list(publish_list)
    replacement_iter = iter(replacements)
    while fresh_count < needed_fresh_count and stale_signal_indexes:
        replacement = next(replacement_iter, None)
        if replacement is None:
            break
        replace_index = stale_signal_indexes.pop(0)
        updated[replace_index] = replacement
        fresh_count += 1
    return updated


def _is_signal_target_fresh(item: dict[str, Any], reference_time: datetime) -> bool:
    age_hours = _age_hours(item, reference_time)
    return age_hours is not None and age_hours <= _SIGNAL_TARGET_WINDOW_HOURS


def _age_hours(item: dict[str, Any], reference_time: datetime) -> float | None:
    event_at = _parse_dt(str(item.get("source_event_at") or item.get("created_at") or item.get("event_at") or ""))
    if event_at is None:
        return None
    return (reference_time - event_at).total_seconds() / 3600.0


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


__all__ = ["build_offline_publish_plan"]
