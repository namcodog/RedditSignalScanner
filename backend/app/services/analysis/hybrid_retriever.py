from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis.search_query import build_websearch_query
from app.services.semantic.embedding_service import MODEL_NAME, embedding_service


@dataclass(frozen=True)
class HybridRetrievalPlan:
    search_query: str
    cutoff_utc: datetime
    limit: int
    vector_distance: float
    hybrid_weight: float


@dataclass(frozen=True)
class HybridRetrievalResult:
    posts: list[dict[str, Any]]
    status: Literal["completed", "skipped", "degraded"]
    reason: str | None = None
    search_query: str | None = None


def _build_summary(title: str, body: str) -> str:
    summary_source = (body or title).strip()
    if len(summary_source) > 200:
        return f"{summary_source[:197]}..."
    return summary_source


def _normalise_row(
    row: Mapping[str, Any],
    *,
    text_rank: float = 0.0,
    semantic_score: float = 0.0,
) -> dict[str, Any]:
    title = str(row.get("title") or "")
    body = str(row.get("body") or "")
    url = str(row.get("url") or "")
    return {
        "id": str(row.get("source_post_id") or row.get("id") or ""),
        "db_id": str(row.get("id") or ""),
        "title": title,
        "summary": _build_summary(title, body),
        "selftext": body,
        "body": body,
        "score": int(row.get("score") or 0),
        "num_comments": int(row.get("num_comments") or 0),
        "url": url,
        "permalink": url,
        "author": str(row.get("author_name") or ""),
        "subreddit": str(row.get("subreddit") or ""),
        "_text_rank": float(text_rank or 0.0),
        "_semantic_score": float(semantic_score or 0.0),
    }


def _merge_scores(
    payload: dict[str, Any],
    *,
    text_rank: float | None = None,
    semantic_score: float | None = None,
) -> None:
    if text_rank is not None:
        payload["_text_rank"] = max(float(payload.get("_text_rank") or 0.0), text_rank)
    if semantic_score is not None:
        payload["_semantic_score"] = max(
            float(payload.get("_semantic_score") or 0.0), semantic_score
        )
def _build_search_query(topic_tokens: Sequence[str]) -> str | None:
    return build_websearch_query(topic_tokens)


def _build_plan(
    *,
    topic_tokens: Sequence[str],
    days: int,
    limit: int,
    vector_distance: float,
    hybrid_weight: float,
) -> HybridRetrievalPlan | None:
    search_query = _build_search_query(topic_tokens)
    if not search_query:
        return None
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=max(int(days), 0))
    return HybridRetrievalPlan(
        search_query=search_query,
        cutoff_utc=cutoff_utc,
        limit=int(limit),
        vector_distance=float(vector_distance),
        hybrid_weight=float(hybrid_weight),
    )


async def fetch_hybrid_posts(
    session: AsyncSession,
    *,
    topic: str,
    topic_tokens: Sequence[str],
    days: int,
    limit: int = 200,
    vector_distance: float = 0.4,
    hybrid_weight: float = 0.7,
) -> list[dict[str, Any]]:
    result = await run_hybrid_retrieval(
        session,
        topic=topic,
        topic_tokens=topic_tokens,
        days=days,
        limit=limit,
        vector_distance=vector_distance,
        hybrid_weight=hybrid_weight,
    )
    return result.posts


async def run_hybrid_retrieval(
    session: AsyncSession,
    *,
    topic: str,
    topic_tokens: Sequence[str],
    days: int,
    limit: int = 200,
    vector_distance: float = 0.4,
    hybrid_weight: float = 0.7,
) -> HybridRetrievalResult:
    plan = _build_plan(
        topic_tokens=topic_tokens,
        days=days,
        limit=limit,
        vector_distance=vector_distance,
        hybrid_weight=hybrid_weight,
    )
    if plan is None:
        return HybridRetrievalResult(posts=[], status="skipped", reason="no_search_terms")

    posts: dict[str, dict[str, Any]] = {}
    degraded_reasons: list[str] = []

    sql_fulltext = text(
        """
        SELECT
            p.id,
            p.source_post_id,
            p.title,
            p.body,
            p.subreddit,
            p.score,
            p.num_comments,
            p.url,
            p.author_name,
            ts_rank_cd(
                to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.body, '')),
                websearch_to_tsquery('english', :search_query)
            ) AS text_rank
        FROM posts_raw p
        WHERE p.created_at >= :cutoff_utc
          AND p.is_current = true
          AND COALESCE(p.is_duplicate, false) = false
          AND COALESCE(p.is_deleted, false) = false
          AND (p.business_pool IS NULL OR p.business_pool <> 'noise')
          AND to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.body, ''))
              @@ websearch_to_tsquery('english', :search_query)
        ORDER BY text_rank DESC
        LIMIT :limit
        """
    )

    try:
        fulltext_rows = await session.execute(
            sql_fulltext,
            {
                "cutoff_utc": plan.cutoff_utc,
                "search_query": plan.search_query,
                "limit": plan.limit,
            },
        )
        for row in fulltext_rows.mappings().all():
            payload = _normalise_row(row, text_rank=float(row.get("text_rank") or 0.0))
            post_id = payload.get("db_id") or payload.get("id")
            if post_id:
                posts[str(post_id)] = payload
    except Exception:
        degraded_reasons.append("fulltext_query_failed")

    try:
        topic_embedding = embedding_service.encode(topic)
    except Exception:
        topic_embedding = None
        degraded_reasons.append("embedding_unavailable")

    if topic_embedding is not None:
        topic_embedding_str = str(topic_embedding)
        sql_semantic = text(
            """
            SELECT
                p.id,
                p.source_post_id,
                p.title,
                p.body,
                p.subreddit,
                p.score,
                p.num_comments,
                p.url,
                p.author_name,
                (1 - (pe.embedding <=> :topic_embedding)) AS semantic_score
            FROM posts_raw p
            JOIN post_embeddings pe
              ON pe.post_id = p.id AND pe.model_version = :model_version
            WHERE p.created_at >= :cutoff_utc
              AND p.is_current = true
              AND COALESCE(p.is_duplicate, false) = false
              AND COALESCE(p.is_deleted, false) = false
              AND (p.business_pool IS NULL OR p.business_pool <> 'noise')
              AND pe.embedding <=> :topic_embedding < :distance
            ORDER BY semantic_score DESC
            LIMIT :limit
            """
        )
        try:
            semantic_rows = await session.execute(
                sql_semantic,
                {
                    "cutoff_utc": plan.cutoff_utc,
                    "topic_embedding": topic_embedding_str,
                    "distance": plan.vector_distance,
                    "limit": plan.limit,
                    "model_version": MODEL_NAME,
                },
            )
            for row in semantic_rows.mappings().all():
                payload = _normalise_row(
                    row, semantic_score=float(row.get("semantic_score") or 0.0)
                )
                post_id = payload.get("db_id") or payload.get("id")
                if not post_id:
                    continue
                key = str(post_id)
                if key in posts:
                    _merge_scores(
                        posts[key],
                        semantic_score=float(row.get("semantic_score") or 0.0),
                    )
                else:
                    posts[key] = payload
        except Exception:
            degraded_reasons.append("semantic_query_failed")

    blended: list[dict[str, Any]] = []
    for payload in posts.values():
        text_rank = float(payload.pop("_text_rank", 0.0))
        semantic_score = float(payload.pop("_semantic_score", 0.0))
        if text_rank and semantic_score:
            score = plan.hybrid_weight * semantic_score + (1 - plan.hybrid_weight) * text_rank
        else:
            score = semantic_score or text_rank
        payload["hybrid_score"] = round(float(score), 6)
        blended.append(payload)

    blended.sort(key=lambda item: float(item.get("hybrid_score") or 0.0), reverse=True)
    if degraded_reasons:
        return HybridRetrievalResult(
            posts=blended[: plan.limit],
            status="degraded",
            reason=",".join(degraded_reasons),
            search_query=plan.search_query,
        )
    return HybridRetrievalResult(
        posts=blended[: plan.limit],
        status="completed",
        search_query=plan.search_query,
    )


__all__ = [
    "HybridRetrievalPlan",
    "HybridRetrievalResult",
    "fetch_hybrid_posts",
    "run_hybrid_retrieval",
]
