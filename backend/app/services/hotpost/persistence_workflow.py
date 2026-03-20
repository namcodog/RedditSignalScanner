from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.hotpost import Hotpost, HotpostSearchResponse
from app.services.hotpost.result_meta import HotpostLLMReportResult


@dataclass(slots=True)
class HotpostPersistenceWorkflowInput:
    query_id: uuid.UUID
    request_query: str
    search_query: str
    keywords: list[str]
    top_posts: list[Hotpost]
    response: HotpostSearchResponse
    llm_report_result: HotpostLLMReportResult
    cache_key: str
    cache_ttl_seconds: int
    comments_cache_ttl_seconds: int
    latency_ms: int
    api_calls: int
    subreddits: list[str] | None


@dataclass(slots=True)
class HotpostPersistenceWorkflowDeps:
    db: AsyncSession
    redis_client: Redis
    upsert_evidence_post: Callable[..., Awaitable[Any]]
    insert_query_evidence_map: Callable[..., Awaitable[Any]]
    maybe_discover_community: Callable[..., Awaitable[None]]
    update_hotpost_query: Callable[..., Awaitable[None]]


@dataclass(slots=True)
class HotpostPersistenceWorkflowResult:
    evidence_count: int
    community_count: int
    comments_cache_entries: int
    discovered_communities: int


def _build_top_comment_refs(post: Hotpost) -> list[dict[str, Any]]:
    return [
        {
            "comment_fullname": comment.comment_fullname,
            "permalink": comment.permalink,
            "score": int(comment.score or 0),
        }
        for comment in post.top_comments
    ]


async def persist_hotpost_search_side_effects(
    *,
    workflow_input: HotpostPersistenceWorkflowInput,
    deps: HotpostPersistenceWorkflowDeps,
) -> HotpostPersistenceWorkflowResult:
    comments_cache: dict[str, list[dict[str, Any]]] = {}
    communities = [post.subreddit for post in workflow_input.top_posts]

    for idx, post in enumerate(workflow_input.top_posts[:30], start=1):
        evidence = await deps.upsert_evidence_post(
            deps.db,
            probe_source="hotpost",
            source_query=workflow_input.search_query,
            source_post_id=post.id,
            subreddit=post.subreddit,
            title=post.title,
            summary=post.body_preview,
            score=post.score,
            num_comments=post.num_comments,
            post_created_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
            evidence_score=int(post.signal_score),
        )
        await deps.insert_query_evidence_map(
            deps.db,
            query_id=workflow_input.query_id,
            evidence_id=evidence.id,
            rank=idx,
            signal_score=post.signal_score,
            signals=post.signals,
            top_comment_refs=_build_top_comment_refs(post),
        )
        comments_cache[str(evidence.id)] = [
            comment.model_dump() for comment in post.top_comments
        ]

    await deps.redis_client.setex(
        f"hotpost:comments:{workflow_input.query_id}",
        workflow_input.comments_cache_ttl_seconds,
        json.dumps(comments_cache, ensure_ascii=False),
    )

    community_counts = Counter(communities)
    for subreddit, count in community_counts.items():
        await deps.maybe_discover_community(
            deps.db,
            subreddit=subreddit,
            evidence_count=count,
            query=workflow_input.request_query,
            keywords=workflow_input.keywords,
        )

    if workflow_input.llm_report_result.report:
        await deps.redis_client.setex(
            f"hotpost:llm_report:{workflow_input.query_id}",
            workflow_input.cache_ttl_seconds,
            json.dumps(workflow_input.llm_report_result.report, ensure_ascii=False),
        )

    await deps.update_hotpost_query(
        deps.db,
        query_id=workflow_input.query_id,
        evidence_count=len(workflow_input.top_posts),
        community_count=len(community_counts),
        confidence=workflow_input.response.confidence,
        from_cache=False,
        latency_ms=workflow_input.latency_ms,
        api_calls=workflow_input.api_calls,
        subreddits=workflow_input.subreddits,
    )

    response_json = workflow_input.response.model_dump_json()
    await deps.redis_client.setex(
        workflow_input.cache_key,
        workflow_input.cache_ttl_seconds,
        response_json,
    )
    await deps.redis_client.setex(
        f"hotpost:result:{workflow_input.query_id}",
        workflow_input.cache_ttl_seconds,
        response_json,
    )

    return HotpostPersistenceWorkflowResult(
        evidence_count=len(workflow_input.top_posts),
        community_count=len(community_counts),
        comments_cache_entries=len(comments_cache),
        discovered_communities=len(community_counts),
    )


__all__ = [
    "HotpostPersistenceWorkflowDeps",
    "HotpostPersistenceWorkflowInput",
    "HotpostPersistenceWorkflowResult",
    "persist_hotpost_search_side_effects",
]
