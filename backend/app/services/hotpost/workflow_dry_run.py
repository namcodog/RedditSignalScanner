from __future__ import annotations

from collections import Counter

from app.services.hotpost.breakdown_draft_materializer import materialize_breakdown_drafts
from app.services.hotpost.breakdown_overlap_audit import audit_breakdown_overlap
from app.services.hotpost.card_candidate_store import list_candidates
from app.services.hotpost.card_draft_store import list_drafts
from app.services.hotpost.card_lane_policy import infer_validation_lane
from app.services.hotpost.card_payload_store import load_published_cards
from app.services.hotpost.card_selection_policy import build_lane_mix_snapshot, build_scope_mix_snapshot
from app.services.hotpost.hotpost_supply_contract import (
    get_supply_collect_profile,
    get_supply_operation_defaults,
    get_supply_rolling_publish_mix,
)
from app.services.hotpost.source_scope_candidate_collector import collect_scope_candidates
from app.services.hotpost.source_scope_catalog import list_source_scopes


async def run_hotpost_workflow_dry_run(
    *,
    max_candidates:Optional[ int] = None,
    queue_limit:Optional[ int] = None,
    materialize_limit:Optional[ int] = None,
    mode: str = "harvest",
) -> dict[str, object]:
    operation_defaults = get_supply_operation_defaults()
    collect_profile = get_supply_collect_profile(mode)
    resolved_max_candidates = int(max_candidates or collect_profile["max_candidates_per_scope"])
    resolved_queue_limit = int(queue_limit or operation_defaults["review_queue_limit"])
    resolved_materialize_limit = int(materialize_limit or operation_defaults["breakdown_materialize_limit"])
    collect_results: dict[str, int] = {}
    for scope in list_source_scopes():
        items = await collect_scope_candidates(scope.source_scope_id, max_candidates=resolved_max_candidates, mode=mode)
        collect_results[scope.source_scope_id] = len(items)
    candidates = list_candidates()
    signal_queue = [_candidate_preview(item) for item in candidates[:resolved_queue_limit]]
    breakdown_results = await materialize_breakdown_drafts(limit=resolved_materialize_limit)
    write_drafts = list_drafts(card_type="write")
    write_queue = [_draft_preview(item) for item in write_drafts[:resolved_queue_limit]]
    overlap = audit_breakdown_overlap()
    published = load_published_cards()
    return {
        "operation_targets": operation_defaults,
        "run_parameters": {
            "mode": mode,
            "max_candidates_per_scope": resolved_max_candidates,
            "review_queue_limit": resolved_queue_limit,
            "breakdown_materialize_limit": resolved_materialize_limit,
        },
        "collect_results": collect_results,
        "throughput": {
            "collected_total": sum(collect_results.values()),
            "validate_queue_count": len(candidates),
            "write_queue_count": len(write_drafts),
            "breakdown_materialized": sum(item.status == "materialized" for item in breakdown_results),
        },
        "recent_mix": _recent_mix_snapshot(published),
        "validate_queue_summary": _candidate_queue_summary(candidates),
        "write_queue_summary": _draft_queue_summary(write_drafts),
        "signal_queue": signal_queue,
        "breakdown_materialize": {
            "count": len(breakdown_results),
            "materialized": sum(item.status == "materialized" for item in breakdown_results),
            "skipped_existing": sum(item.status == "skipped_existing" for item in breakdown_results),
            "failed": sum(item.status == "failed" for item in breakdown_results),
        },
        "write_queue": write_queue,
        "overlap_pair_count": overlap["pair_count"],
        "next_manual_steps": [
            "review signal drafts before publish",
            "review write drafts before publish",
            "check overlap warnings before publishing breakdown cards",
        ],
    }


def _recent_mix_snapshot(published: list[dict]) -> dict[str, object]:
    rules = get_supply_rolling_publish_mix()
    lane_counts = build_lane_mix_snapshot(published)
    scope_counts = build_scope_mix_snapshot(published)
    return {
        "window_size": rules["window_size"],
        "lane_counts": lane_counts,
        "lane_targets": rules["lane_targets"],
        "lane_gaps": _gap_snapshot(rules["lane_targets"], lane_counts),
        "scope_counts": scope_counts,
        "scope_targets": rules["scope_targets"],
        "scope_gaps": _gap_snapshot(rules["scope_targets"], scope_counts),
    }


def _candidate_queue_summary(items) -> dict[str, object]:
    lane_counts = Counter(infer_validation_lane(item) for item in items)
    scope_counts = Counter(item.source_scope_id for item in items)
    return {
        "total": len(items),
        "lane_counts": dict(lane_counts),
        "scope_counts": dict(scope_counts),
    }


def _draft_queue_summary(items) -> dict[str, object]:
    scope_counts = Counter(item.source_scope_id for item in items)
    return {
        "total": len(items),
        "scope_counts": dict(scope_counts),
    }


def _gap_snapshot(targets: dict[str, int], counts: dict[str, int]) -> dict[str, int]:
    return {key: int(target) - int(counts.get(key, 0)) for key, target in targets.items()}


def _candidate_preview(item) -> dict[str, object]:
    return {
        "candidate_id": item.candidate_id,
        "scope": item.source_scope_id,
        "topic_pack_id": item.topic_pack_id,
        "signal_level": item.signal_level,
        "title": item.title,
    }


def _draft_preview(item) -> dict[str, object]:
    return {
        "draft_id": item.draft_id,
        "card_type": item.card_type,
        "scope": item.source_scope_id,
        "title": item.title,
    }


__all__ = ["run_hotpost_workflow_dry_run"]
