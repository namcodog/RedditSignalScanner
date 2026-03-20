from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import text as sqltext

from app.db.session import SessionFactory
from app.services.llm.comment_label_planner import HIGH_SCORE_MIN, LOW_SCORE_MAX
from app.services.llm.label_batch_support import split_limits

DEFAULT_HIGH_SCORE_RATIO = 0.3


async def fetch_incremental_post_candidates(
    *,
    limit: int,
    lookback_days: int,
    session_factory: Callable[[], Any] = SessionFactory,
    low_score_max: float = LOW_SCORE_MAX,
    high_score_min: float = HIGH_SCORE_MIN,
    high_score_ratio: float = DEFAULT_HIGH_SCORE_RATIO,
) -> list[dict[str, Any]]:
    async with session_factory() as session:
        mid_limit, high_limit = split_limits(limit, high_score_ratio)
        rows: list[dict[str, Any]] = []
        seen: set[int] = set()
        base_params = {"days": int(lookback_days)}

        if mid_limit > 0:
            result = await session.execute(
                sqltext(
                    """
                    SELECT p.id,
                           p.title,
                           p.body,
                           p.subreddit,
                           p.score,
                           p.num_comments,
                           p.text_norm_hash,
                           p.source,
                           p.source_post_id,
                           p.url,
                           ps.value_score,
                           ps.business_pool
                    FROM posts_raw p
                    JOIN post_scores_latest_v ps ON ps.post_id = p.id
                    LEFT JOIN post_llm_labels llm ON llm.post_id = p.id
                    LEFT JOIN post_llm_labels llm_hash
                      ON p.text_norm_hash IS NOT NULL
                     AND llm_hash.text_norm_hash = p.text_norm_hash
                    WHERE p.is_current = TRUE
                      AND ps.business_pool IN ('core','lab')
                      AND p.created_at >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.post_id IS NULL
                      AND llm_hash.post_id IS NULL
                      AND ps.value_score > :low_score
                      AND ps.value_score < :high_score
                    ORDER BY ps.value_score DESC, p.score DESC, p.num_comments DESC
                    LIMIT :limit
                    """
                ),
                {
                    **base_params,
                    "limit": int(mid_limit),
                    "low_score": low_score_max,
                    "high_score": high_score_min,
                },
            )
            for row in result.mappings().all():
                post_id = int(row["id"])
                if post_id in seen:
                    continue
                seen.add(post_id)
                rows.append(row)

        if high_limit > 0:
            result = await session.execute(
                sqltext(
                    """
                    SELECT p.id,
                           p.title,
                           p.body,
                           p.subreddit,
                           p.score,
                           p.num_comments,
                           p.text_norm_hash,
                           p.source,
                           p.source_post_id,
                           p.url,
                           ps.value_score,
                           ps.business_pool
                    FROM posts_raw p
                    JOIN post_scores_latest_v ps ON ps.post_id = p.id
                    LEFT JOIN post_llm_labels llm ON llm.post_id = p.id
                    LEFT JOIN post_llm_labels llm_hash
                      ON p.text_norm_hash IS NOT NULL
                     AND llm_hash.text_norm_hash = p.text_norm_hash
                    WHERE p.is_current = TRUE
                      AND ps.business_pool IN ('core','lab')
                      AND p.created_at >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.post_id IS NULL
                      AND llm_hash.post_id IS NULL
                      AND ps.value_score >= :high_score
                    ORDER BY ps.value_score DESC, p.score DESC, p.num_comments DESC
                    LIMIT :limit
                    """
                ),
                {
                    **base_params,
                    "limit": int(high_limit),
                    "high_score": high_score_min,
                },
            )
            for row in result.mappings().all():
                post_id = int(row["id"])
                if post_id in seen:
                    continue
                seen.add(post_id)
                rows.append(row)

        return rows


async def fetch_post_top_comments(
    *,
    source: str,
    source_post_id: str,
    limit: int,
    session_factory: Callable[[], Any] = SessionFactory,
) -> list[str]:
    async with session_factory() as session:
        rows = await session.execute(
            sqltext(
                """
                SELECT body
                FROM comments
                WHERE source = :source
                  AND source_post_id = :post_id
                ORDER BY score DESC NULLS LAST
                LIMIT :limit
                """
            ),
            {"source": source, "post_id": source_post_id, "limit": int(limit)},
        )
        return [str(row.body or "") for row in rows]


__all__ = [
    "DEFAULT_HIGH_SCORE_RATIO",
    "fetch_incremental_post_candidates",
    "fetch_post_top_comments",
]
