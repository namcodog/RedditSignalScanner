from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_clues import QuotePreview
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.candidate_group_promoter import build_grouped_candidates
from app.services.hotpost.candidate_spec_collector import (
    _await_comment_tasks,
    _comment_batch_timeout_seconds,
    _task_comments_or_empty,
    collect_candidates_for_spec,
    pack_comments_fetch_limit,
)
from app.services.hotpost.card_candidate_store import replace_scope_candidates
from app.services.hotpost.growth_pack_intake import uses_growth_pack_intake_path
from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile
from app.services.hotpost.hotpost_priority_targets import (
    RECALL_PRIORITY_CLUSTER_IDS,
    has_recall_priority_cluster,
)
from app.services.hotpost.hotpost_supply_projection import get_topic_pack_payload
from app.services.hotpost.quota_aware_crawl import (
    BACKFILL_PHASE,
    CRAWL_PHASE_ORDER,
    DISCOVER_PHASE,
    ENRICH_PHASE,
    QUOTA_AWARE_CRAWL_WINNER,
    build_enrich_shortlist,
    split_specs_for_crawl,
)
from app.services.hotpost.reddit_search_spec_builder import build_reddit_search_specs
from app.services.hotpost.source_scope_catalog import build_topic_pack_candidate_quotas
from app.services.hotpost.topic_metadata import normalize_topic_metadata
from app.services.infrastructure.reddit_collect_client import build_collect_reddit_client


async def collect_scope_candidates(
    scope_id: SourceScopeId,
    *,
    max_candidates: int | None = None,
    mode: str = "harvest",
    dry_cycles: int = 0,
    enable_secondary_discover_assist: bool = False,
    include_experimental: bool = False,
    experimental_only: bool = False,
    persist: bool = True,
) -> list[CandidatePack]:
    summary = await collect_scope_candidates_with_summary(
        scope_id,
        max_candidates=max_candidates,
        mode=mode,
        dry_cycles=dry_cycles,
        enable_secondary_discover_assist=enable_secondary_discover_assist,
        include_experimental=include_experimental,
        experimental_only=experimental_only,
        persist=persist,
    )
    return list(summary["items"])


async def collect_scope_candidates_with_summary(
    scope_id: SourceScopeId,
    *,
    max_candidates: int | None = None,
    mode: str = "harvest",
    dry_cycles: int = 0,
    enable_secondary_discover_assist: bool = False,
    include_experimental: bool = False,
    experimental_only: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    imported: dict[str, CandidatePack] = {}
    comment_cache: dict[str, list[dict[str, Any]]] = {}
    comment_tasks: dict[str, asyncio.Task[list[dict[str, Any]]]] = {}
    subreddit_counts: dict[tuple[str, str], int] = {}
    collect_defaults = get_supply_collect_profile(mode)
    target_max_candidates = int(max_candidates or collect_defaults["max_candidates_per_scope"])
    quotas = build_topic_pack_candidate_quotas(scope_id, target_max_candidates)
    specs = _limit_specs_by_budget(
        _build_scope_search_specs(
            scope_id,
            include_experimental=include_experimental,
            experimental_only=experimental_only,
        ),
        collect_defaults=collect_defaults,
        dry_cycles=dry_cycles,
    )
    phases = split_specs_for_crawl(specs)
    comment_timeout = int(collect_defaults.get("comment_request_timeout") or 8)
    collected_at = datetime.now(timezone.utc)
    collect_batch_id = f"{scope_id}-{collected_at.strftime('%Y%m%d%H%M%S')}"
    phase_summaries: list[dict[str, Any]] = []

    async with build_collect_reddit_client(
        request_timeout=20.0,
        search_timeout=12.0,
        max_concurrency=max(1, int(collect_defaults.get("api_max_concurrency") or 2)),
        low_quota_remaining_threshold=int(collect_defaults.get("low_quota_remaining_threshold") or 12),
        low_quota_cooldown_seconds=float(collect_defaults.get("low_quota_cooldown_seconds") or 20),
        stop_comment_fetch_below_remaining=int(collect_defaults.get("stop_comment_fetch_below_remaining") or 18),
        max_consecutive_rate_limit_errors=int(collect_defaults.get("max_consecutive_rate_limit_errors") or 3),
    ) as reddit:
        phase_summaries.append(
            await _collect_phase(
                reddit=reddit,
                phase=DISCOVER_PHASE,
                scope_id=scope_id,
                specs=phases[DISCOVER_PHASE],
                collect_batch_id=collect_batch_id,
                collected_at=collected_at,
                comment_timeout=comment_timeout,
                comment_cache=comment_cache,
                comment_tasks=comment_tasks,
                imported=imported,
                subreddit_counts=subreddit_counts,
                quotas=quotas,
                target_max_candidates=target_max_candidates,
                spec_batch_size=max(1, int(collect_defaults.get("spec_batch_size") or 2)),
                enrich_comments=False,
                assist_secondary_discover=enable_secondary_discover_assist,
            )
        )
        shortlist = _build_shortlist_for_enrich(imported.values(), target_max_candidates=target_max_candidates)
        if shortlist:
            phase_summaries.append(
                await _enrich_shortlist(
                    reddit=reddit,
                    shortlist=shortlist,
                    comment_cache=comment_cache,
                    comment_tasks=comment_tasks,
                    imported=imported,
                    comment_timeout=comment_timeout,
                )
            )
        else:
            phase_summaries.append(
                _empty_phase_summary(
                    phase=ENRICH_PHASE,
                    specs=[],
                    imported_count=len(imported),
                    shortlist_size=0,
                )
            )
        phase_summaries.append(
            await _collect_phase(
                reddit=reddit,
                phase=BACKFILL_PHASE,
                scope_id=scope_id,
                specs=phases[BACKFILL_PHASE],
                collect_batch_id=collect_batch_id,
                collected_at=collected_at,
                comment_timeout=comment_timeout,
                comment_cache=comment_cache,
                comment_tasks=comment_tasks,
                imported=imported,
                subreddit_counts=subreddit_counts,
                quotas=quotas,
                target_max_candidates=target_max_candidates,
                spec_batch_size=max(1, int(collect_defaults.get("spec_batch_size") or 2)),
                enrich_comments=False,
                assist_secondary_discover=False,
            )
        )
        final_shortlist = _build_shortlist_for_enrich(imported.values(), target_max_candidates=target_max_candidates)
        if final_shortlist:
            await _enrich_shortlist(
                reddit=reddit,
                shortlist=final_shortlist,
                comment_cache=comment_cache,
                comment_tasks=comment_tasks,
                imported=imported,
                comment_timeout=comment_timeout,
            )
        collect_stats = _snapshot_collect_stats(reddit)

    items = [*list(imported.values()), *build_grouped_candidates(list(imported.values()))]
    if persist:
        replace_scope_candidates(scope_id, items)
    return {
        "items": items,
        "scope_id": scope_id,
        "mode": mode,
        "dry_cycles_seen": dry_cycles,
        "winner": QUOTA_AWARE_CRAWL_WINNER,
        "phase_order": list(CRAWL_PHASE_ORDER),
        "phase_summaries": phase_summaries,
        "shortlist_size": len(final_shortlist),
        "secondary_discover_assist_enabled": enable_secondary_discover_assist,
        "experimental_probe_enabled": include_experimental,
        "experimental_only": experimental_only,
        "persisted_to_formal_candidates": persist,
        "collect_stats": collect_stats,
        "providers": {
            "post_discovery": "reddit_api_primary",
            "comment_enrichment": "reddit_api_primary_with_sociavault_assist_rescue",
            "sociavault_role": "assist+rescue",
        },
    }


def _build_scope_search_specs(
    scope_id: SourceScopeId,
    *,
    include_experimental: bool,
    experimental_only: bool,
) -> list[Any]:
    if not include_experimental:
        return build_reddit_search_specs(scope_id)
    specs = build_reddit_search_specs(scope_id, include_experimental=True)
    if experimental_only:
        return [spec for spec in specs if _is_experimental_spec(spec)]
    return specs


def _is_experimental_spec(spec: Any) -> bool:
    return bool(getattr(spec, "is_experimental_probe", False))


async def _collect_phase(
    *,
    reddit: Any,
    phase: str,
    scope_id: SourceScopeId,
    specs: list[Any],
    collect_batch_id: str,
    collected_at: datetime,
    comment_timeout: int,
    comment_cache: dict[str, list[dict[str, Any]]],
    comment_tasks: dict[str, asyncio.Task[list[dict[str, Any]]]],
    imported: dict[str, CandidatePack],
    subreddit_counts: dict[tuple[str, str], int],
    quotas: dict[str, int],
    target_max_candidates: int,
    spec_batch_size: int,
    enrich_comments: bool,
    assist_secondary_discover: bool,
    selected_post_ids: set[str] | None = None,
) -> dict[str, Any]:
    before_imported = len(imported)
    before_stats = _snapshot_collect_stats(reddit)
    execution_specs = _prioritize_specs_for_recall(
        _prioritize_discover_specs_for_assist(
            specs,
            phase=phase,
            assist_secondary_discover=assist_secondary_discover,
            spec_batch_size=spec_batch_size,
        )
    )
    for batch in _batched(execution_specs, spec_batch_size):
        active_specs = [spec for spec in batch if not _topic_pack_quota_reached(imported, spec.topic_pack_id, quotas)]
        if not active_specs:
            continue
        batch_results = await asyncio.gather(
            *[
                collect_candidates_for_spec(
                    reddit,
                    scope_id,
                    spec,
                    collect_batch_id=collect_batch_id,
                    collected_at=collected_at,
                    comment_timeout=comment_timeout,
                    comment_cache=comment_cache,
                    comment_tasks=comment_tasks,
                    enrich_comments=enrich_comments,
                    selected_post_ids=selected_post_ids,
                    prefer_fallback_for_posts=_should_use_secondary_discover_assist(
                        phase=phase,
                        spec=spec,
                        assist_secondary_discover=assist_secondary_discover,
                    ),
                )
                for spec in active_specs
            ]
        )
        for spec_candidates in batch_results:
            for candidate in spec_candidates:
                if candidate.candidate_id in imported:
                    current = imported[candidate.candidate_id]
                    imported[candidate.candidate_id] = _merge_duplicate_candidate(current, candidate)
                    continue
                if _topic_pack_quota_reached(imported, candidate.topic_pack_id, quotas):
                    continue
                topic_pack_id = candidate.topic_pack_id
                if topic_pack_id and _subreddit_cap_reached(subreddit_counts, topic_pack_id, candidate.matched_subreddit, scope_id):
                    continue
                imported[candidate.candidate_id] = candidate
                key = (candidate.topic_pack_id or "", candidate.matched_subreddit.lower())
                subreddit_counts[key] = subreddit_counts.get(key, 0) + 1
                if len(imported) >= target_max_candidates:
                    return _phase_summary(
                        phase=phase,
                        specs=specs,
                        imported_before=before_imported,
                        imported_after=len(imported),
                        stats_before=before_stats,
                        stats_after=_snapshot_collect_stats(reddit),
                        enrich_comments=enrich_comments,
                        assist_secondary_discover=assist_secondary_discover,
                        selected_post_ids=selected_post_ids,
                    )
    return _phase_summary(
        phase=phase,
        specs=specs,
        imported_before=before_imported,
        imported_after=len(imported),
        stats_before=before_stats,
        stats_after=_snapshot_collect_stats(reddit),
        enrich_comments=enrich_comments,
        assist_secondary_discover=assist_secondary_discover,
        selected_post_ids=selected_post_ids,
    )


async def _enrich_shortlist(
    *,
    reddit: Any,
    shortlist: list[CandidatePack],
    comment_cache: dict[str, list[dict[str, Any]]],
    comment_tasks: dict[str, asyncio.Task[list[dict[str, Any]]]],
    imported: dict[str, CandidatePack],
    comment_timeout: int,
) -> dict[str, Any]:
    before_imported = len(imported)
    before_stats = _snapshot_collect_stats(reddit)
    selected_post_ids = {candidate.post_id for candidate in shortlist}
    pending_tasks: list[asyncio.Task[list[dict[str, Any]]]] = []
    for candidate in shortlist:
        if candidate.post_id in comment_cache:
            continue
        task = comment_tasks.get(candidate.post_id)
        if task is None:
            task = asyncio.create_task(
                reddit.fetch_post_comments(
                    candidate.post_id,
                    sort="top",
                    depth=1,
                    limit=pack_comments_fetch_limit(candidate.source_scope_id, candidate.topic_pack_id),
                    mode="topn",
                    comment_timeout=float(comment_timeout),
                )
            )
            comment_tasks[candidate.post_id] = task
        pending_tasks.append(task)
    if pending_tasks:
        await _await_comment_tasks(
            pending_tasks,
            timeout_seconds=_comment_batch_timeout_seconds(reddit, comment_timeout=float(comment_timeout)),
            log_context={
                "scope_id": shortlist[0].source_scope_id if shortlist else None,
                "topic_pack_id": shortlist[0].topic_pack_id if shortlist else None,
                "subreddit": shortlist[0].matched_subreddit if shortlist else None,
                "phase": ENRICH_PHASE,
            },
        )
    for candidate in shortlist:
        if candidate.post_id in comment_cache:
            continue
        task = comment_tasks.pop(candidate.post_id, None)
        if task is None:
            continue
        comment_cache[candidate.post_id] = _task_comments_or_empty(
            task,
            log_context={
                "scope_id": candidate.source_scope_id,
                "topic_pack_id": candidate.topic_pack_id,
                "subreddit": candidate.matched_subreddit,
                "phase": ENRICH_PHASE,
                "post_id": candidate.post_id,
            },
        )
    _refresh_shortlist_quotes(imported, shortlist, comment_cache)
    return _phase_summary(
        phase=ENRICH_PHASE,
        specs=[],
        imported_before=before_imported,
        imported_after=len(imported),
        stats_before=before_stats,
        stats_after=_snapshot_collect_stats(reddit),
        enrich_comments=True,
        assist_secondary_discover=False,
        selected_post_ids=selected_post_ids,
    )


def _batched(specs: list[Any], batch_size: int) -> list[list[Any]]:
    return [specs[index : index + batch_size] for index in range(0, len(specs), batch_size)]


def _build_shortlist_for_enrich(candidates: Any, *, target_max_candidates: int) -> list[CandidatePack]:
    candidate_list = list(candidates)
    return build_enrich_shortlist(
        candidate_list,
        max_items=max(2, min(len(candidate_list), max(4, target_max_candidates // 2))),
    )


def _snapshot_collect_stats(reddit: Any) -> dict[str, int]:
    if hasattr(reddit, "get_collect_stats"):
        raw = reddit.get_collect_stats()
        if isinstance(raw, dict):
            return {str(key): int(value) for key, value in raw.items()}
    return {}


def _stats_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    keys = set(before) | set(after)
    return {key: int(after.get(key, 0)) - int(before.get(key, 0)) for key in sorted(keys)}


def _phase_summary(
    *,
    phase: str,
    specs: list[Any],
    imported_before: int,
    imported_after: int,
    stats_before: dict[str, int],
    stats_after: dict[str, int],
    enrich_comments: bool,
    assist_secondary_discover: bool,
    selected_post_ids: set[str] | None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "spec_count": len(specs),
        "enrich_comments": enrich_comments,
        "secondary_discover_assist_enabled": assist_secondary_discover if phase == DISCOVER_PHASE else False,
        "selected_post_count": len(selected_post_ids or ()),
        "imported_candidates": max(0, imported_after - imported_before),
        "candidate_total_after_phase": imported_after,
        "collect_stats": _stats_delta(stats_before, stats_after),
    }


def _empty_phase_summary(
    *,
    phase: str,
    specs: list[Any],
    imported_count: int,
    shortlist_size: int,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "spec_count": len(specs),
        "enrich_comments": phase == ENRICH_PHASE,
        "secondary_discover_assist_enabled": False,
        "selected_post_count": shortlist_size,
        "imported_candidates": 0,
        "candidate_total_after_phase": imported_count,
        "collect_stats": {},
    }


def _should_use_secondary_discover_assist(
    *,
    phase: str,
    spec: Any,
    assist_secondary_discover: bool,
) -> bool:
    if not assist_secondary_discover or phase != DISCOVER_PHASE:
        return False
    if getattr(spec, "mode", "") == "search":
        return True
    return getattr(spec, "sort", "") == "new"


def _prioritize_discover_specs_for_assist(
    specs: list[Any],
    *,
    phase: str,
    assist_secondary_discover: bool,
    spec_batch_size: int,
) -> list[Any]:
    if not assist_secondary_discover or phase != DISCOVER_PHASE:
        return list(specs)
    primary_specs = [spec for spec in specs if not _should_use_secondary_discover_assist(
        phase=phase,
        spec=spec,
        assist_secondary_discover=True,
    )]
    secondary_specs = [spec for spec in specs if _should_use_secondary_discover_assist(
        phase=phase,
        spec=spec,
        assist_secondary_discover=True,
    )]
    if not primary_specs or not secondary_specs:
        return list(specs)
    primary_window = max(2, spec_batch_size * 2)
    secondary_window = max(1, spec_batch_size)
    return [
        *primary_specs[:primary_window],
        *secondary_specs[:secondary_window],
        *primary_specs[primary_window:],
        *secondary_specs[secondary_window:],
    ]


def _limit_specs_by_budget(specs: list[Any], *, collect_defaults: dict[str, Any], dry_cycles: int = 0) -> list[Any]:
    search_budget = _resolve_budget(collect_defaults, "max_search_specs_per_scope", 120)
    listing_budget = _resolve_budget(collect_defaults, "max_listing_specs_per_scope", 36)
    phases = split_specs_for_crawl(specs)
    discover_specs = list(phases.get(DISCOVER_PHASE) or [])
    backfill_specs = list(phases.get(BACKFILL_PHASE) or [])
    backfill_search_budget = _backfill_budget(search_budget, dry_cycles=dry_cycles)
    backfill_listing_budget = _backfill_budget(listing_budget, dry_cycles=dry_cycles)
    backfill_search_specs = _prioritize_specs_for_recall(
        [spec for spec in backfill_specs if getattr(spec, "mode", "") == "search"]
    )[:backfill_search_budget]
    backfill_listing_specs = _prioritize_specs_for_recall(
        sorted(
            [spec for spec in backfill_specs if getattr(spec, "mode", "") == "listing"],
            key=lambda spec: (
                0
                if uses_growth_pack_intake_path(getattr(spec, "source_scope_id", ""), getattr(spec, "topic_pack_id", None))
                else 1
            ),
        )
    )[:backfill_listing_budget]
    return [*discover_specs, *backfill_listing_specs, *backfill_search_specs]


def _resolve_budget(collect_defaults: dict[str, int], key: str, default: int) -> int:
    raw = collect_defaults.get(key)
    if raw is None:
        return default
    return max(0, int(raw))


def _backfill_budget(budget: int, *, dry_cycles: int) -> int:
    if budget <= 0:
        return 0
    if dry_cycles <= 0:
        return budget
    if dry_cycles == 1:
        return max(1, budget // 2)
    return 0


def _prioritize_specs_for_recall(specs: list[Any]) -> list[Any]:
    if len(specs) <= 1:
        return list(specs)
    pack_order: list[str] = []
    grouped_specs: dict[str, list[Any]] = {}
    for spec in specs:
        pack_id = str(getattr(spec, "topic_pack_id", "") or "")
        if pack_id not in grouped_specs:
            pack_order.append(pack_id)
            grouped_specs[pack_id] = []
        grouped_specs[pack_id].append(spec)
    prioritized: list[Any] = []
    for pack_id in pack_order:
        pack_specs = grouped_specs[pack_id]
        priority_buckets: dict[str, list[Any]] = {cluster_id: [] for cluster_id in RECALL_PRIORITY_CLUSTER_IDS}
        non_priority_cluster_order: list[str] = []
        non_priority_buckets: dict[str, list[Any]] = {}
        non_priority_specs: list[Any] = []
        for spec in pack_specs:
            priority_cluster_id = _spec_recall_priority_cluster_id(spec)
            if priority_cluster_id is None:
                cluster_id = _spec_primary_cluster_id(spec)
                if cluster_id is None:
                    non_priority_specs.append(spec)
                    continue
                if cluster_id not in non_priority_buckets:
                    non_priority_cluster_order.append(cluster_id)
                    non_priority_buckets[cluster_id] = []
                non_priority_buckets[cluster_id].append(spec)
                continue
            priority_buckets[priority_cluster_id].append(spec)
        prioritized.extend(_interleave_cluster_buckets(priority_buckets, list(RECALL_PRIORITY_CLUSTER_IDS)))
        prioritized.extend(_interleave_cluster_buckets(non_priority_buckets, non_priority_cluster_order))
        prioritized.extend(non_priority_specs)
    return prioritized


def _spec_has_recall_priority_cluster(spec: Any) -> bool:
    return has_recall_priority_cluster(
        getattr(spec, "topic_cluster_id", None),
        getattr(spec, "topic_cluster_ids", None),
    )


def _spec_recall_priority_cluster_id(spec: Any) -> str | None:
    cluster_ids = {
        str(item).strip()
        for item in (getattr(spec, "topic_cluster_ids", None) or ())
        if str(item).strip()
    }
    topic_cluster_id = str(getattr(spec, "topic_cluster_id", "") or "").strip()
    if topic_cluster_id:
        cluster_ids.add(topic_cluster_id)
    for cluster_id in RECALL_PRIORITY_CLUSTER_IDS:
        if cluster_id in cluster_ids:
            return cluster_id
    return None


def _spec_primary_cluster_id(spec: Any) -> str | None:
    topic_cluster_id = str(getattr(spec, "topic_cluster_id", "") or "").strip()
    if topic_cluster_id:
        return topic_cluster_id
    for item in (getattr(spec, "topic_cluster_ids", None) or ()):
        cluster_id = str(item).strip()
        if cluster_id:
            return cluster_id
    return None


def _interleave_cluster_buckets(
    buckets: dict[str, list[Any]],
    cluster_order: list[str],
) -> list[Any]:
    ordered: list[Any] = []
    if not cluster_order:
        return ordered
    pending = {cluster_id: list(buckets.get(cluster_id) or []) for cluster_id in cluster_order}
    while any(pending.values()):
        for cluster_id in cluster_order:
            bucket = pending[cluster_id]
            if bucket:
                ordered.append(bucket.pop(0))
    return ordered


def _merge_duplicate_candidate(current: CandidatePack, incoming: CandidatePack) -> CandidatePack:
    preferred = current if current.quote_count >= incoming.quote_count else incoming
    merged_metadata = normalize_topic_metadata(
        topic_pack_id=preferred.topic_pack_id or current.topic_pack_id or incoming.topic_pack_id,
        topic_cluster_id=preferred.topic_cluster_id or current.topic_cluster_id or incoming.topic_cluster_id,
        topic_cluster_ids=[
            *current.topic_cluster_ids,
            *incoming.topic_cluster_ids,
            *([current.topic_cluster_id] if current.topic_cluster_id else []),
            *([incoming.topic_cluster_id] if incoming.topic_cluster_id else []),
        ],
        named_topic_ids=[*current.named_topic_ids, *incoming.named_topic_ids],
    )
    merged_communities = list(dict.fromkeys([*current.top_communities, *incoming.top_communities]))
    merged_quotes = list(
        {
            (
                str(item.text).strip(),
                str(item.permalink).strip(),
            ): item
            for item in [*current.evidence_quotes, *incoming.evidence_quotes]
        }.values()
    )
    return preferred.model_copy(
        update={
            **merged_metadata,
            "matched_keywords": list(dict.fromkeys([*current.matched_keywords, *incoming.matched_keywords])),
            "top_communities": merged_communities,
            "community_count": max(
                current.community_count,
                incoming.community_count,
                len({community for community in merged_communities if str(community).strip()}),
            ),
            "quote_count": max(current.quote_count, incoming.quote_count, len(merged_quotes)),
            "intent_tags": list(dict.fromkeys([*current.intent_tags, *incoming.intent_tags])),
            "evidence_quotes": merged_quotes[:2],
        }
    )


def _topic_pack_quota_reached(imported: dict[str, CandidatePack], topic_pack_id: str | None, quotas: dict[str, int]) -> bool:
    if not topic_pack_id:
        return False
    allowed = quotas.get(topic_pack_id)
    if allowed is None:
        return False
    current = sum(1 for item in imported.values() if item.topic_pack_id == topic_pack_id)
    return current >= allowed


def _subreddit_cap_reached(
    counts: dict[tuple[str, str], int],
    topic_pack_id: str,
    subreddit: str,
    scope_id: SourceScopeId,
) -> bool:
    payload = get_topic_pack_payload(scope_id, topic_pack_id)
    cap = int(payload.get("subreddit_candidate_cap") or 2)
    key = (topic_pack_id, subreddit.lower())
    return counts.get(key, 0) >= cap


def _refresh_shortlist_quotes(
    imported: dict[str, CandidatePack],
    shortlist: list[CandidatePack],
    comment_cache: dict[str, list[dict[str, Any]]],
) -> None:
    for candidate in shortlist:
        comments = comment_cache.get(candidate.post_id) or []
        quotes = [_comment_quote(candidate, item) for item in comments if _usable_comment(item)]
        current = imported.get(candidate.candidate_id)
        if current is None:
            continue
        imported[candidate.candidate_id] = current.model_copy(
            update={
                "quote_count": len(quotes),
                "evidence_quotes": quotes[:2],
            }
        )


def _usable_comment(comment: dict[str, Any]) -> bool:
    body = str(comment.get("body") or "").strip()
    lowered = body.lower()
    return (
        len(body) >= 20
        and not body.startswith("[removed]")
        and "automoderator" not in lowered
        and "i am a bot" not in lowered
    )


def _comment_quote(candidate: CandidatePack, comment: dict[str, Any]) -> QuotePreview:
    permalink = str(comment.get("permalink") or "").strip()
    if permalink and not permalink.startswith("http"):
        permalink = f"https://www.reddit.com{permalink}"
    return QuotePreview(
        text=str(comment.get("body") or "").strip(),
        community=f"r/{candidate.matched_subreddit}",
        permalink=permalink or f"https://www.reddit.com/comments/{candidate.post_id}",
    )


__all__ = [
    "collect_scope_candidates",
    "collect_scope_candidates_with_summary",
]
