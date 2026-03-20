from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.schemas.hotpost import Hotpost, HotpostDebugInfo, HotpostSearchRequest, PainPoint
from app.services.hotpost.evidence_collection_workflow import (
    HotpostEvidenceCollectionDeps,
    HotpostEvidenceCollectionResult,
)
from app.services.hotpost.persistence_workflow import HotpostPersistenceWorkflowDeps
from app.services.hotpost.queue import HotpostQueueTracker
from app.services.hotpost.report_workflow import HotpostReportWorkflowDeps
from app.services.hotpost.response_bundle import (
    build_hotpost_debug_info,
    build_hotpost_search_response,
    resolve_hotpost_response,
)
from app.services.hotpost.search_workflow import HotpostSearchWorkflowDeps


@dataclass(slots=True)
class HotpostSearchDepsFactoryInput:
    db: Any
    redis_client: Any
    lexicon: Any
    reddit_client: Any
    llm_client: Any | None
    getenv: Callable[[str, str], str]
    resolve_query: Callable[..., Awaitable[Any]]
    create_hotpost_query: Callable[..., Awaitable[None]]
    update_hotpost_query: Callable[..., Awaitable[None]]
    collect_evidence: Callable[..., Awaitable[HotpostEvidenceCollectionResult]]
    build_report_result: Callable[..., Awaitable[Any]]
    persist_side_effects: Callable[..., Awaitable[Any]]
    maybe_discover_community: Callable[..., Awaitable[Any]]
    upsert_evidence_post: Callable[..., Awaitable[Any]]
    insert_query_evidence_map: Callable[..., Awaitable[Any]]
    tracker_factory: Callable[..., Any] = HotpostQueueTracker
    resolve_mode: Callable[[HotpostSearchRequest], str] | None = None
    resolve_time_filter: Callable[[str, HotpostSearchRequest], str] | None = None
    resolve_sort: Callable[[str], str] | None = None
    split_search_queries: Callable[[str, int], list[str]] | None = None
    acquire_rate_budget: Callable[..., Awaitable[None]] | None = None
    search_subreddit_posts: Callable[..., Awaitable[Any]] | None = None
    fetch_comments: Callable[..., Awaitable[Any]] | None = None
    select_signals: Callable[[str, str], dict[str, list[str]]] | None = None
    sentiment_label: Callable[[str, str, dict[str, list[str]]], str] | None = None
    build_post: Callable[..., Hotpost] | None = None
    build_pain_points: Callable[[list[Hotpost], list[str]], list[PainPoint]] | None = None
    confidence_level: Callable[[int], str] | None = None
    maybe_llm_summary: Callable[..., Awaitable[Any]] | None = None


def build_hotpost_response_status(
    *,
    resolution_reason: str | None,
    summary_result: Any,
    report_result: Any,
) -> tuple[str, list[str]]:
    return resolve_hotpost_response(
        resolution_reason=resolution_reason,
        summary_result=summary_result,
        report_result=report_result,
    )


def build_hotpost_debug_contract(
    *,
    resolution_source: str,
    resolution_reason: str | None,
    search_query: str,
    query_parts: list[str],
    keywords: list[str],
    time_filter: str,
    sort: str,
    subreddits: list[str] | None,
    raw_posts: int,
    filtered_posts: int,
    relevance_filtered: int,
    summary_result: Any,
    report_result: Any,
    degraded_reasons: list[str],
    response_source: str,
) -> HotpostDebugInfo:
    return build_hotpost_debug_info(
        resolution_source=resolution_source,
        resolution_reason=resolution_reason,
        search_query=search_query,
        query_parts=query_parts,
        keywords=keywords,
        time_filter=time_filter,
        sort=sort,
        subreddits=subreddits,
        raw_posts=raw_posts,
        filtered_posts=filtered_posts,
        relevance_filtered=relevance_filtered,
        summary_result=summary_result,
        report_result=report_result,
        degraded_reasons=degraded_reasons,
        response_source=response_source,
    )


def build_hotpost_search_deps(factory_input: HotpostSearchDepsFactoryInput) -> HotpostSearchWorkflowDeps:
    assert factory_input.resolve_mode is not None
    assert factory_input.resolve_time_filter is not None
    assert factory_input.resolve_sort is not None
    assert factory_input.split_search_queries is not None
    assert factory_input.acquire_rate_budget is not None
    assert factory_input.search_subreddit_posts is not None
    assert factory_input.fetch_comments is not None
    assert factory_input.select_signals is not None
    assert factory_input.sentiment_label is not None
    assert factory_input.build_post is not None
    assert factory_input.build_pain_points is not None
    assert factory_input.confidence_level is not None
    assert factory_input.maybe_llm_summary is not None

    async def _resolve_query(query: str) -> Any:
        return await factory_input.resolve_query(
            query,
            redis_client=factory_input.redis_client,
            llm_client=factory_input.llm_client,
        )

    return HotpostSearchWorkflowDeps(
        redis_client=factory_input.redis_client,
        getenv=factory_input.getenv,
        resolve_mode=factory_input.resolve_mode,
        resolve_time_filter=factory_input.resolve_time_filter,
        resolve_sort=factory_input.resolve_sort,
        split_search_queries=lambda search_query, max_chars: factory_input.split_search_queries(
            search_query,
            max_chars=max_chars,
        ),
        resolve_query=_resolve_query,
        create_hotpost_query=lambda **kwargs: factory_input.create_hotpost_query(factory_input.db, **kwargs),
        update_hotpost_query=lambda **kwargs: factory_input.update_hotpost_query(factory_input.db, **kwargs),
        tracker_factory=factory_input.tracker_factory,
        collect_evidence=factory_input.collect_evidence,
        maybe_llm_summary=factory_input.maybe_llm_summary,
        build_report_result=factory_input.build_report_result,
        build_search_response=build_hotpost_search_response,
        persist_side_effects=factory_input.persist_side_effects,
        evidence_deps_factory=lambda: HotpostEvidenceCollectionDeps(
            acquire_rate_budget=factory_input.acquire_rate_budget,
            search_subreddits=factory_input.reddit_client.search_subreddits,
            search_subreddit_posts=factory_input.search_subreddit_posts,
            search_posts=factory_input.reddit_client.search_posts,
            fetch_comments=factory_input.fetch_comments,
            select_signals=factory_input.select_signals,
            sentiment_label=factory_input.sentiment_label,
            build_post=factory_input.build_post,
            build_pain_points=factory_input.build_pain_points,
            confidence_level=factory_input.confidence_level,
            lexicon=factory_input.lexicon,
        ),
        report_deps_factory=HotpostReportWorkflowDeps,
        persistence_deps_factory=lambda: HotpostPersistenceWorkflowDeps(
            db=factory_input.db,
            redis_client=factory_input.redis_client,
            upsert_evidence_post=factory_input.upsert_evidence_post,
            insert_query_evidence_map=factory_input.insert_query_evidence_map,
            maybe_discover_community=factory_input.maybe_discover_community,
            update_hotpost_query=factory_input.update_hotpost_query,
        ),
    )


__all__ = [
    "HotpostSearchDepsFactoryInput",
    "build_hotpost_debug_contract",
    "build_hotpost_response_status",
    "build_hotpost_search_deps",
]
