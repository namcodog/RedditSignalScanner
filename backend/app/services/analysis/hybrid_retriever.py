from __future__ import annotations

from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.semantic.embedding_service import MODEL_NAME, embedding_service


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
    tokens = [t.strip().lower() for t in topic_tokens or [] if t and t.strip()]
    if not tokens:
        return []

    search_query = " | ".join(tokens)

    try:
        topic_embedding = embedding_service.encode(topic)
        has_embedding = True
    except Exception:
        topic_embedding = None
        has_embedding = False

    posts: dict[str, dict[str, Any]] = {}

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
                to_tsquery('english', :search_query)
            ) AS text_rank
        FROM posts_raw p
        WHERE p.created_at >= NOW() - (:days * INTERVAL '1 day')
          AND p.is_current = true
          AND COALESCE(p.is_duplicate, false) = false
          AND COALESCE(p.is_deleted, false) = false
          AND (p.business_pool IS NULL OR p.business_pool <> 'noise')
          AND to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.body, ''))
              @@ to_tsquery('english', :search_query)
        ORDER BY text_rank DESC
        LIMIT :limit
        """
    )

    fulltext_rows = await session.execute(
        sql_fulltext, {"days": int(days), "search_query": search_query, "limit": limit}
    )
    for row in fulltext_rows.mappings().all():
        payload = _normalise_row(row, text_rank=float(row.get("text_rank") or 0.0))
        post_id = payload.get("db_id") or payload.get("id")
        if post_id:
            posts[str(post_id)] = payload

    if has_embedding and topic_embedding is not None:
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
            WHERE p.created_at >= NOW() - (:days * INTERVAL '1 day')
              AND p.is_current = true
              AND COALESCE(p.is_duplicate, false) = false
              AND COALESCE(p.is_deleted, false) = false
              AND (p.business_pool IS NULL OR p.business_pool <> 'noise')
              AND pe.embedding <=> :topic_embedding < :distance
            ORDER BY semantic_score DESC
            LIMIT :limit
            """
        )
        semantic_rows = await session.execute(
            sql_semantic,
            {
                "days": int(days),
                "topic_embedding": topic_embedding_str,
                "distance": float(vector_distance),
                "limit": limit,
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

    blended: list[dict[str, Any]] = []
    for payload in posts.values():
        text_rank = float(payload.pop("_text_rank", 0.0))
        semantic_score = float(payload.pop("_semantic_score", 0.0))
        if text_rank and semantic_score:
            score = hybrid_weight * semantic_score + (1 - hybrid_weight) * text_rank
        else:
            score = semantic_score or text_rank
        payload["hybrid_score"] = round(float(score), 6)
        blended.append(payload)

    blended.sort(key=lambda item: float(item.get("hybrid_score") or 0.0), reverse=True)
    return blended[:limit]


__all__ = ["fetch_hybrid_posts"]
