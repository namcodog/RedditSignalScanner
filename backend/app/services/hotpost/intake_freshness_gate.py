from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional, Any

from app.services.hotpost.card_candidate_store import list_candidates
from app.services.hotpost.card_draft_store import list_drafts
from app.services.hotpost.card_lane_policy import infer_validation_lane
from app.services.hotpost.hotpost_supply_contract import get_supply_operation_defaults, resolve_supply_lane_targets


LANE_WINDOWS_HOURS = {
    "hot": {"target": 24.0, "max": 48.0},
    "signal": {"target": 72.0, "max": 120.0},
    "breakdown": {"target": 24.0 * 7.0, "max": 24.0 * 10.0},
}

def evaluate_publish_plan(payload: dict[str, Any], *, target_total: int | None = None) -> dict[str, Any]:
    items = _plan_items(payload)
    reference_time = _parse_dt(str(payload.get("generated_at") or "")) or datetime.now(timezone.utc)
    resolved_target_total = int(target_total or get_supply_operation_defaults()["min_cards_per_run"])
    lane_targets = _target_lane_counts(resolved_target_total)
    topic_tree_governance = dict(payload.get("topic_tree_governance") or {})
    draft_index, candidate_index = _load_indexes()
    total_items = len(items)
    yield_exhausted = total_items == 0

    lane_counts: Counter[str] = Counter()
    target_fresh_counts: Counter[str] = Counter()
    acceptable_fresh_counts: Counter[str] = Counter()
    stale_counts: Counter[str] = Counter()
    unknown_age_count = 0
    max_age_hours_by_lane: dict[str, float] = {}
    item_rows: list[dict[str, Any]] = []

    for item in items:
        lane = str(item.get("lane") or "")
        lane_counts[lane] += 1
        event_at, source_payload = _resolve_event_at(item, draft_index=draft_index, candidate_index=candidate_index)
        age_hours:Optional[ float] = None
        if event_at is None:
            unknown_age_count += 1
        else:
            age_hours = (reference_time - event_at).total_seconds() / 3600.0
            windows = LANE_WINDOWS_HOURS.get(lane)
            if windows:
                if age_hours <= windows["target"]:
                    target_fresh_counts[lane] += 1
                if age_hours <= windows["max"]:
                    acceptable_fresh_counts[lane] += 1
                else:
                    stale_counts[lane] += 1
                max_age_hours_by_lane[lane] = max(max_age_hours_by_lane.get(lane, 0.0), age_hours)
        item_rows.append(
            {
                "candidate_id": item.get("candidate_id"),
                "draft_id": item.get("draft_id"),
                "lane": lane,
                "topic_pack_id": item.get("topic_pack_id"),
                "title": item.get("title"),
                "age_hours": round(age_hours, 1) if age_hours is not None else None,
                "time_window": (source_payload or {}).get("time_window"),
            }
        )

    total_stale = sum(stale_counts.values()) + unknown_age_count
    stale_ratio = (total_stale / total_items) if total_items else 0.0
    fresh_publish_ratio = sum(target_fresh_counts.values()) / total_items if total_items else 0.0

    hot_count = lane_counts.get("hot", 0)
    signal_count = lane_counts.get("signal", 0)
    breakdown_count = lane_counts.get("breakdown", 0)

    hot_freshness_pass = acceptable_fresh_counts.get("hot", 0) == hot_count
    signal_majority_floor = _ceil_majority(signal_count) if signal_count else 0
    signal_freshness_pass = target_fresh_counts.get("signal", 0) >= signal_majority_floor
    breakdown_freshness_pass = acceptable_fresh_counts.get("breakdown", 0) == breakdown_count
    stale_ratio_pass = stale_ratio <= 0.2
    window_target_met = total_items >= resolved_target_total
    candidate_freshness = _load_candidate_freshness_by_lane(reference_time)

    rewrite_reasons: list[str] = []
    fail_reasons: list[str] = []

    if not yield_exhausted and stale_ratio > 0.4:
        fail_reasons.append("stale_ratio_out_of_control")

    if not yield_exhausted and not fail_reasons:
        if hot_count > 0 and not hot_freshness_pass:
            rewrite_reasons.append("hot_over_age_limit")
        if signal_count > 0 and not signal_freshness_pass:
            rewrite_reasons.append("signal_target_window_underfilled")
        if breakdown_count > 0 and not breakdown_freshness_pass:
            rewrite_reasons.append("breakdown_over_age_limit")
        if not stale_ratio_pass:
            rewrite_reasons.append("stale_ratio_above_threshold")
        if unknown_age_count:
            rewrite_reasons.append("unknown_event_time_present")

    if fail_reasons:
        decision = "fail"
    elif rewrite_reasons:
        decision = "rewrite"
    else:
        decision = "publish"

    recommended_actions: list[str] = []
    if decision != "publish":
        scope = str(payload.get("scope") or "").strip()
        plan_output = f"backend/tmp/offline-publish-plan-{resolved_target_total}.json"
        plan_command = (
            f".venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py "
            f"--limit {resolved_target_total} --output {plan_output}"
        )
        if scope:
            plan_command = (
                f".venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py "
                f"--limit {resolved_target_total} --scope {scope} --output {plan_output}"
            )
        recommended_actions.extend(
            [
                ".venv/bin/python backend/scripts/hotpost/daily_collect.py",
                ".venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json",
                plan_command,
            ]
        )
        if should_escalate_named_topic_collect(
            decision=decision,
            rewrite_reasons=rewrite_reasons,
            fail_reasons=fail_reasons,
            lane_counts=dict(lane_counts),
            candidate_freshness_by_lane=candidate_freshness,
        ):
            recommended_actions.insert(1, ".venv/bin/python backend/scripts/hotpost/collect_named_topics.py")

    return {
        "harness_id": "reddit-signal-scanner-intake-freshness-v1",
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "plan_generated_at": reference_time.isoformat().replace("+00:00", "Z"),
        "target_total": resolved_target_total,
        "actual_total": total_items,
        "yield_exhausted": yield_exhausted,
        "lane_targets": lane_targets,
        "lane_counts": dict(lane_counts),
        "window_target_met": window_target_met,
        "target_fresh_counts": dict(target_fresh_counts),
        "acceptable_fresh_counts": dict(acceptable_fresh_counts),
        "stale_counts": dict(stale_counts),
        "unknown_age_count": unknown_age_count,
        "max_age_hours_by_lane": {lane: round(hours, 1) for lane, hours in max_age_hours_by_lane.items()},
        "signal_majority_floor": signal_majority_floor,
        "fresh_publish_ratio": round(fresh_publish_ratio, 4),
        "stale_ratio": round(stale_ratio, 4),
        "candidate_freshness_by_lane": candidate_freshness,
        "topic_tree_governance": topic_tree_governance,
        "checks": {
            "hot_freshness_pass": hot_freshness_pass,
            "signal_freshness_pass": signal_freshness_pass,
            "breakdown_freshness_pass": breakdown_freshness_pass,
            "stale_ratio_pass": stale_ratio_pass,
        },
        "decision": decision,
        "rewrite_reasons": rewrite_reasons,
        "fail_reasons": fail_reasons,
        "recommended_actions": recommended_actions,
        "items": item_rows,
    }


def _parse_dt(value:Optional[ str]) ->Optional[ datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _plan_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    items = plan.get("publish_list")
    if isinstance(items, list):
        return items
    items = plan.get("cards")
    if isinstance(items, list):
        return items
    if isinstance(plan, list):
        return plan
    raise ValueError("Unsupported publish plan shape")


def _load_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    draft_index = {
        str(draft.draft_id): draft.model_dump(mode="json")
        for draft in list_drafts()
    }
    candidate_index = {
        str(candidate.candidate_id): candidate.model_dump(mode="json")
        for candidate in list_candidates()
    }
    return draft_index, candidate_index


def _resolve_event_at(
    item: dict[str, Any],
    *,
    draft_index: dict[str, dict[str, Any]],
    candidate_index: dict[str, dict[str, Any]],
) -> tuple[Optional[datetime], Optional[dict[str, Any]]]:
    direct = item.get("source_event_at") or item.get("created_at") or item.get("event_at")
    if direct:
        return _parse_dt(str(direct)), item

    source_type = str(item.get("source_type") or "")
    if source_type == "draft":
        draft = draft_index.get(str(item.get("draft_id") or ""))
        return _parse_dt((draft or {}).get("source_event_at")), draft

    candidate = candidate_index.get(str(item.get("candidate_id") or ""))
    return _parse_dt((candidate or {}).get("created_at")), candidate


def _target_lane_counts(target_total: int) -> dict[str, int]:
    return resolve_supply_lane_targets(target_total)


def should_escalate_named_topic_collect(
    *,
    decision: str,
    rewrite_reasons: list[str],
    fail_reasons: list[str],
    lane_counts: dict[str, int],
    candidate_freshness_by_lane: dict[str, dict[str, Any]],
) -> bool:
    if decision == "publish":
        return False
    reasons = set(rewrite_reasons) | set(fail_reasons)
    if "hot_over_age_limit" not in reasons and "stale_ratio_out_of_control" not in reasons:
        return False
    hot_count = int(lane_counts.get("hot") or 0)
    if hot_count <= 0:
        return False
    hot_candidate_fresh = candidate_freshness_by_lane.get("hot") or {}
    hot_candidate_acceptable = int(hot_candidate_fresh.get("acceptable_fresh") or 0)
    return hot_candidate_acceptable < hot_count


def _ceil_majority(count: int) -> int:
    return math.floor(count / 2) + 1


def _load_candidate_freshness_by_lane(reference_time: datetime) -> dict[str, dict[str, Any]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for candidate in list_candidates():
        lane = infer_validation_lane(candidate)
        hours = (reference_time - candidate.created_at).total_seconds() / 3600.0
        counts[lane]["total"] += 1
        if hours <= LANE_WINDOWS_HOURS[lane]["target"]:
            counts[lane]["target_fresh"] += 1
        if hours <= LANE_WINDOWS_HOURS[lane]["max"]:
            counts[lane]["acceptable_fresh"] += 1
        else:
            counts[lane]["stale"] += 1

    return {
        lane: {
            "total": values["total"],
            "target_fresh": values["target_fresh"],
            "acceptable_fresh": values["acceptable_fresh"],
            "stale": values["stale"],
            "target_fresh_ratio": round(values["target_fresh"] / values["total"], 4) if values["total"] else 0.0,
        }
        for lane, values in counts.items()
    }


__all__ = [
    "LANE_WINDOWS_HOURS",
    "evaluate_publish_plan",
    "should_escalate_named_topic_collect",
]
