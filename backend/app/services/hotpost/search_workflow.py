from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.schemas.hotpost import HotpostDebugInfo, HotpostSearchRequest, HotpostSearchResponse
from app.services.hotpost.cache import build_hotpost_cache_key, get_hotpost_cache_ttl_seconds
from app.services.hotpost.evidence_collection_workflow import (
    HotpostEvidenceCollectionDeps,
    HotpostEvidenceCollectionInput,
    HotpostEvidenceCollectionResult,
)
from app.services.hotpost.persistence_workflow import (
    HotpostPersistenceWorkflowDeps,
    HotpostPersistenceWorkflowInput,
)
from app.services.hotpost.report_workflow import (
    HotpostReportWorkflowDeps,
    HotpostReportWorkflowInput,
)
from app.services.hotpost.result_meta import normalize_hotpost_status
from app.services.hotpost.response_bundle import (
    HotpostResponseBundleInput,
)


@dataclass(slots=True)
class HotpostSearchWorkflowInput:
    request: HotpostSearchRequest
    user_id: uuid.UUID | None = None
    session_id: str | None = None
    ip_hash: str | None = None
    llm_model_name: str = ""
    comments_ttl_seconds: int = 2 * 60 * 60


@dataclass(slots=True)
class HotpostSearchWorkflowDeps:
    redis_client: Any
    getenv: Callable[[str, str], str] = os.getenv
    resolve_mode: Callable[[HotpostSearchRequest], str] | None = None
    resolve_time_filter: Callable[[str, HotpostSearchRequest], str] | None = None
    resolve_sort: Callable[[str], str] | None = None
    split_search_queries: Callable[[str, int], list[str]] | None = None
    resolve_query: Callable[[str], Awaitable[Any]] | None = None
    create_hotpost_query: Callable[..., Awaitable[None]] | None = None
    update_hotpost_query: Callable[..., Awaitable[None]] | None = None
    tracker_factory: Callable[..., Any] | None = None
    collect_evidence: Callable[..., Awaitable[HotpostEvidenceCollectionResult]] | None = None
    maybe_llm_summary: Callable[..., Awaitable[Any]] | None = None
    build_report_result: Callable[..., Awaitable[Any]] | None = None
    build_search_response: Callable[[HotpostResponseBundleInput], HotpostSearchResponse] | None = None
    persist_side_effects: Callable[..., Awaitable[Any]] | None = None
    evidence_deps_factory: Callable[[], HotpostEvidenceCollectionDeps] | None = None
    report_deps_factory: Callable[[], HotpostReportWorkflowDeps] | None = None
    persistence_deps_factory: Callable[[], HotpostPersistenceWorkflowDeps] | None = None


@dataclass(slots=True)
class HotpostSearchWorkflowResult:
    response: HotpostSearchResponse


def _env_flag(getenv: Callable[[str, str], str], key: str, default: str = "true") -> bool:
    return getenv(key, default).strip().lower() in {"1", "true", "yes"}


async def run_hotpost_search_workflow(
    *,
    workflow_input: HotpostSearchWorkflowInput,
    deps: HotpostSearchWorkflowDeps,
) -> HotpostSearchWorkflowResult:
    assert deps.resolve_mode is not None
    assert deps.resolve_time_filter is not None
    assert deps.resolve_sort is not None
    assert deps.split_search_queries is not None
    assert deps.resolve_query is not None
    assert deps.create_hotpost_query is not None
    assert deps.update_hotpost_query is not None
    assert deps.tracker_factory is not None
    assert deps.collect_evidence is not None
    assert deps.maybe_llm_summary is not None
    assert deps.build_report_result is not None
    assert deps.build_search_response is not None
    assert deps.persist_side_effects is not None
    assert deps.evidence_deps_factory is not None
    assert deps.report_deps_factory is not None
    assert deps.persistence_deps_factory is not None

    start_time = time.monotonic()
    query_id = uuid.uuid4()
    request = workflow_input.request

    mode = deps.resolve_mode(request)
    time_filter = deps.resolve_time_filter(mode, request)
    sort = deps.resolve_sort(mode)

    resolution = await deps.resolve_query(request.query)
    search_query = resolution.search_query or request.query
    keywords = resolution.keywords or search_query.split()
    subreddits = request.subreddits or (resolution.subreddits if resolution.subreddits else None)

    notes: list[str] = []
    max_query_chars = int(deps.getenv("HOTPOST_QUERY_MAX_CHARS", "50"))
    max_query_splits = int(deps.getenv("HOTPOST_MAX_QUERY_SPLITS", "3"))
    query_parts = deps.split_search_queries(search_query, max_query_chars)
    if len(query_parts) > max_query_splits:
        query_parts = query_parts[:max_query_splits]
        notes.append(f"关键词过长，已拆分为 {max_query_splits} 次查询（已截断）")
    elif len(query_parts) > 1:
        notes.append(f"关键词过长，已拆分为 {len(query_parts)} 次查询")

    cache_key = build_hotpost_cache_key(search_query, mode, subreddits)
    cache_ttl_seconds = get_hotpost_cache_ttl_seconds(mode)

    await deps.create_hotpost_query(
        query_id=query_id,
        query=request.query,
        mode=mode,
        time_filter=time_filter,
        subreddits=request.subreddits,
        user_id=workflow_input.user_id,
        session_id=workflow_input.session_id,
        ip_hash=workflow_input.ip_hash,
        evidence_count=0,
        community_count=0,
        confidence="none",
        from_cache=False,
        latency_ms=None,
        api_calls=None,
    )
    queue_tracker = deps.tracker_factory(
        deps.redis_client,
        str(query_id),
        ttl_seconds=cache_ttl_seconds,
    )
    await queue_tracker.mark_processing()

    cached_raw = await deps.redis_client.get(cache_key)
    if cached_raw:
        payload = json.loads(cached_raw)
        payload["from_cache"] = True
        payload["search_time"] = datetime.now(timezone.utc).isoformat()
        payload["status"] = normalize_hotpost_status(payload.get("status"))
        debug_info = dict(payload.get("debug_info") or {})
        debug_info["response_source"] = "cache"
        payload["debug_info"] = HotpostDebugInfo(**debug_info).model_dump()
        await deps.update_hotpost_query(
            query_id=query_id,
            evidence_count=payload.get("evidence_count", 0),
            community_count=len(payload.get("communities", [])),
            confidence=payload.get("confidence", "low"),
            from_cache=True,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            api_calls=0,
            subreddits=request.subreddits,
        )
        await queue_tracker.mark_completed()
        return HotpostSearchWorkflowResult(response=HotpostSearchResponse(**payload))

    enable_relevance_filter = _env_flag(deps.getenv, "ENABLE_HOTPOST_RELEVANCE_FILTER", "true")
    evidence = await deps.collect_evidence(
        workflow_input=HotpostEvidenceCollectionInput(
            request_query=request.query,
            query_parts=query_parts,
            keywords=keywords,
            mode=mode,
            time_filter=time_filter,
            sort=sort,
            limit=request.limit,
            requested_subreddits=None
            if mode == "opportunity" and request.subreddits is None
            else subreddits,
            suggest_subreddits_when_missing=mode != "opportunity",
            enable_relevance_filter=enable_relevance_filter,
            max_posts_per_subreddit=min(100, max(30, request.limit)),
            notes=notes,
        ),
        deps=deps.evidence_deps_factory(),
        queue_tracker=queue_tracker,
    )

    summary_result = await deps.maybe_llm_summary(
        query=request.query,
        posts=evidence.top_posts,
        confidence=evidence.confidence,
        sentiment_overview=evidence.sentiment_overview,
        community_distribution=evidence.community_distribution,
    )

    llm_report_result = await deps.build_report_result(
        workflow_input=HotpostReportWorkflowInput(
            mode=mode,
            query=request.query,
            time_filter=time_filter,
            top_posts=evidence.top_posts,
            all_comments=evidence.all_comments,
            llm_model_name=workflow_input.llm_model_name,
        ),
        deps=deps.report_deps_factory(),
    )

    response = deps.build_search_response(
        HotpostResponseBundleInput(
            query_id=str(query_id),
            query=request.query,
            mode=mode,
            top_posts=evidence.top_posts,
            all_comments=evidence.all_comments,
            notes=evidence.notes,
            resolution_source=resolution.source,
            resolution_reason=resolution.degraded_reason,
            search_query=search_query,
            query_parts=query_parts,
            keywords=keywords,
            time_filter=time_filter,
            sort=sort,
            subreddits=evidence.subreddits,
            raw_posts=evidence.raw_posts,
            filtered_posts=evidence.filtered_posts,
            relevance_filtered=evidence.relevance_filtered,
            summary_result=summary_result,
            report_result=llm_report_result,
            sentiment_overview=evidence.sentiment_overview,
            confidence=evidence.confidence,
            lexicon=deps.evidence_deps_factory().lexicon,
            me_too_count=evidence.me_too_count,
            pain_points=evidence.pain_points,
            opportunities=evidence.opportunities,
            rant_intensity=evidence.rant_intensity,
            need_urgency=evidence.need_urgency,
            categories=evidence.categories,
        )
    )

    await deps.persist_side_effects(
        workflow_input=HotpostPersistenceWorkflowInput(
            query_id=query_id,
            request_query=request.query,
            search_query=search_query,
            keywords=keywords,
            top_posts=evidence.top_posts,
            response=response,
            llm_report_result=llm_report_result,
            cache_key=cache_key,
            cache_ttl_seconds=cache_ttl_seconds,
            comments_cache_ttl_seconds=workflow_input.comments_ttl_seconds,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            api_calls=evidence.api_calls,
            subreddits=evidence.subreddits,
        ),
        deps=deps.persistence_deps_factory(),
    )
    await queue_tracker.mark_completed()
    return HotpostSearchWorkflowResult(response=response)


__all__ = [
    "HotpostSearchWorkflowDeps",
    "HotpostSearchWorkflowInput",
    "HotpostSearchWorkflowResult",
    "run_hotpost_search_workflow",
]
