from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile
from app.services.hotpost.quota_aware_crawl import (
    CRAWL_PHASE_ORDER,
    DRY_CYCLE_DEFAULT,
    QUOTA_AWARE_CRAWL_WINNER,
    has_publishable_gain,
    measure_publishable_gain,
)
from app.services.hotpost.source_scope_candidate_collector import collect_scope_candidates_with_summary
from app.services.hotpost.source_scope_catalog import list_source_scopes


async def run_quota_aware_collect(
    *,
    scope: str | None,
    mode: str,
    max_candidates: int | None = None,
    dry_cycle_limit: int | None = None,
) -> dict[str, Any]:
    collect_defaults = get_supply_collect_profile(mode)
    effective_max_candidates = int(max_candidates or collect_defaults["max_candidates_per_scope"])
    target_scopes = [item for item in list_source_scopes() if scope in (None, item.source_scope_id)]
    previous_gain = measure_publishable_gain(source_scope_id=scope)
    dry_limit = int(dry_cycle_limit or collect_defaults.get("dry_cycle") or DRY_CYCLE_DEFAULT)
    dry_cycles = 0
    cycle_index = 0
    cycle_rows: list[dict[str, Any]] = []
    total_collect_stats: Counter[str] = Counter()
    secondary_discover_assist_scope_ids: set[str] = set()

    while dry_cycles < dry_limit:
        cycle_index += 1
        imported: dict[str, int] = {}
        cycle_collect_stats: Counter[str] = Counter()
        scope_summaries: dict[str, dict[str, Any]] = {}
        for item in target_scopes:
            scope_summary = await collect_scope_candidates_with_summary(
                item.source_scope_id,
                max_candidates=effective_max_candidates,
                mode=mode,
                dry_cycles=dry_cycles,
                enable_secondary_discover_assist=item.source_scope_id in secondary_discover_assist_scope_ids,
            )
            imported[item.source_scope_id] = len(scope_summary["items"])
            cycle_collect_stats.update(scope_summary["collect_stats"])
            total_collect_stats.update(scope_summary["collect_stats"])
            scope_summaries[item.source_scope_id] = {
                "phase_summaries": scope_summary["phase_summaries"],
                "collect_stats": scope_summary["collect_stats"],
                "shortlist_size": scope_summary["shortlist_size"],
                "secondary_discover_assist_enabled": scope_summary["secondary_discover_assist_enabled"],
            }
        current_gain = measure_publishable_gain(source_scope_id=scope)
        gained = has_publishable_gain(previous_gain, current_gain)
        dry_cycles = 0 if gained else dry_cycles + 1
        next_cycle_secondary_discover_assist_scope_ids = (
            {
                scope_id
                for scope_id, summary in scope_summaries.items()
                if _discover_surface_remaining(summary)
            }
            if dry_cycles >= 2
            else set()
        )
        cycle_rows.append(
            {
                "cycle": cycle_index,
                "imported": imported,
                "publishable_gain_before": previous_gain,
                "publishable_gain_after": current_gain,
                "gain_detected": gained,
                "dry_cycles": dry_cycles,
                "scope_summaries": scope_summaries,
                "next_cycle_secondary_discover_assist_scopes": sorted(next_cycle_secondary_discover_assist_scope_ids),
                "collect_stats": dict(cycle_collect_stats),
            }
        )
        previous_gain = current_gain
        secondary_discover_assist_scope_ids = next_cycle_secondary_discover_assist_scope_ids
        sleep_seconds = _dry_cycle_sleep_seconds(
            collect_defaults=collect_defaults,
            dry_cycles=dry_cycles,
            dry_cycle_limit=dry_limit,
        )
        cycle_rows[-1]["sleep_seconds_before_next_cycle"] = sleep_seconds
        if sleep_seconds > 0:
            await asyncio.sleep(sleep_seconds)

    return {
        "workflow": "quota-aware-yield-until-exhausted-crawl",
        "winner": QUOTA_AWARE_CRAWL_WINNER,
        "phase_order": list(CRAWL_PHASE_ORDER),
        "mode": mode,
        "scope": scope,
        "max_candidates_per_scope": effective_max_candidates,
        "dry_cycle_limit": dry_limit,
        "providers": {
            "post_discovery": "reddit_api_primary",
            "sociavault_role": "assist+rescue",
            "comment_enrichment": "shortlist_only_late_with_assist_rescue",
        },
        "sociavault_triggers": {
            "comments_assist": ["primary_low_quota", "empty_comment_response"],
            "rescue": ["rate_limit", "timed_out", "temporarily_unavailable", "connection_failed"],
            "secondary_discover_assist": ["two_dry_cycles_with_discover_surface_remaining"],
        },
        "cycles": cycle_rows,
        "collect_stats_total": dict(total_collect_stats),
        "final_publishable_gain": previous_gain,
        "stopped_by": "yield_exhaustion",
    }


def _dry_cycle_sleep_seconds(
    *,
    collect_defaults: dict[str, Any],
    dry_cycles: int,
    dry_cycle_limit: int,
) -> float:
    if dry_cycles <= 0 or dry_cycles >= dry_cycle_limit:
        return 0.0
    base_seconds = float(collect_defaults.get("low_quota_cooldown_seconds") or 0)
    if base_seconds <= 0:
        return 0.0
    return base_seconds * float(dry_cycles)


def _discover_surface_remaining(scope_summary: dict[str, Any]) -> bool:
    for phase_summary in scope_summary.get("phase_summaries", []):
        if phase_summary.get("phase") != "discover":
            continue
        spec_count = int(phase_summary.get("spec_count") or 0)
        collect_stats = phase_summary.get("collect_stats") or {}
        total_post_requests = int(collect_stats.get("primary_post_requests") or 0) + int(
            collect_stats.get("fallback_post_requests") or 0
        )
        return spec_count > total_post_requests
    return False


__all__ = ["run_quota_aware_collect"]
