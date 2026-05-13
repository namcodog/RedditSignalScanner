from __future__ import annotations

from typing import Any

from sqlalchemy import text as sqltext

from app.db.session import SessionFactory
from app.services.llm.label_export_io import truncate_text
from app.services.llm.post_label_planner import (
    fetch_incremental_post_candidates,
    fetch_post_top_comments,
)
from app.utils.asyncio_runner import run as run_coro


def export_posts(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
    max_comment_chars: int,
    top_comments: int,
) -> list[dict[str, Any]]:
    rows = run_coro(
        fetch_incremental_post_candidates(
            limit=limit,
            lookback_days=lookback_days,
        )
    ) or []
    payload: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source") or "reddit")
        source_post_id = str(row.get("source_post_id") or "")
        comments: list[str] = []
        if source_post_id:
            comments = run_coro(
                fetch_post_top_comments(
                    source=source,
                    source_post_id=source_post_id,
                    limit=top_comments,
                )
            ) or []
        payload.append(
            {
                "task_type": "post_label",
                "id": int(row.get("id")),
                "subreddit": str(row.get("subreddit") or ""),
                "title": truncate_text(str(row.get("title") or ""), max_body_chars),
                "body": truncate_text(str(row.get("body") or ""), max_body_chars),
                "comments": [
                    truncate_text(str(comment or ""), max_comment_chars)
                    for comment in comments[:top_comments]
                ],
            }
        )
    return payload


async def fetch_post_candidates_all(
    *,
    limit: int,
    lookback_days: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
    noise_min_comments: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"days": int(lookback_days)}
    limit_clause = ""
    if limit > 0:
        limit_clause = "LIMIT :limit"
        params["limit"] = int(limit)

    core_sql = f"""
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
        ORDER BY ps.value_score DESC, p.score DESC, p.num_comments DESC
        {limit_clause}
    """

    async with SessionFactory() as session:
        result = await session.execute(sqltext(core_sql), params)
        rows = [dict(row) for row in result.mappings().all()]

        if include_noise and noise_ratio > 0:
            base_count = int(limit) if limit > 0 else await count_post_candidates_core_lab(
                session=session,
                lookback_days=lookback_days,
            )
            noise_limit = int(base_count * noise_ratio)
            if noise_limit > 0:
                noise_params = {
                    "days": int(lookback_days),
                    "min_score": int(noise_min_score),
                    "min_comments": int(noise_min_comments),
                    "limit": int(noise_limit),
                }
                noise_sql = """
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
                      AND ps.business_pool = 'noise'
                      AND p.created_at >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.post_id IS NULL
                      AND llm_hash.post_id IS NULL
                      AND (p.score >= :min_score OR p.num_comments >= :min_comments)
                    ORDER BY p.score DESC, p.num_comments DESC
                    LIMIT :limit
                """
                noise_result = await session.execute(sqltext(noise_sql), noise_params)
                rows.extend(dict(row) for row in noise_result.mappings().all())
        return rows


async def count_post_candidates_core_lab(
    *,
    session: Any,
    lookback_days: int,
) -> int:
    result = await session.execute(
        sqltext(
            """
            SELECT COUNT(*)
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
            """
        ),
        {"days": int(lookback_days)},
    )
    return int(result.scalar_one())


def export_posts_all(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
    max_comment_chars: int,
    top_comments: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
    noise_min_comments: int,
) -> list[dict[str, Any]]:
    rows = run_coro(
        fetch_post_candidates_all(
            limit=limit,
            lookback_days=lookback_days,
            include_noise=include_noise,
            noise_ratio=noise_ratio,
            noise_min_score=noise_min_score,
            noise_min_comments=noise_min_comments,
        )
    ) or []
    payload: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source") or "reddit")
        source_post_id = str(row.get("source_post_id") or "")
        comments: list[str] = []
        if source_post_id:
            comments = run_coro(
                fetch_post_top_comments(
                    source=source,
                    source_post_id=source_post_id,
                    limit=top_comments,
                )
            ) or []
        payload.append(
            {
                "task_type": "post_label",
                "id": int(row.get("id")),
                "subreddit": str(row.get("subreddit") or ""),
                "title": truncate_text(str(row.get("title") or ""), max_body_chars),
                "body": truncate_text(str(row.get("body") or ""), max_body_chars),
                "comments": [
                    truncate_text(str(comment or ""), max_comment_chars)
                    for comment in comments[:top_comments]
                ],
            }
        )
    return payload


__all__ = [
    "count_post_candidates_core_lab",
    "export_posts",
    "export_posts_all",
    "fetch_post_candidates_all",
]
