from __future__ import annotations

from typing import Any

from sqlalchemy import text as sqltext

from app.db.session import SessionFactory
from app.services.llm.comment_label_planner import (
    build_comment_activation_export_plan,
    build_historical_comment_activation_plan,
    build_incremental_comment_label_plan,
)
from app.services.llm.label_export_io import comment_payload_from_row, truncate_text
from app.utils.asyncio_runner import run as run_coro


def export_comments(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
) -> list[dict[str, Any]]:
    plan = run_coro(
        build_incremental_comment_label_plan(limit=limit, lookback_days=lookback_days)
    )
    rows = plan.candidates if plan is not None else []
    return [
        {
            "task_type": "comment_label",
            "id": int(row.get("id")),
            "subreddit": str(row.get("subreddit") or ""),
            "post_title": truncate_text(str(row.get("post_title") or ""), max_body_chars),
            "comment_body": truncate_text(str(row.get("body") or ""), max_body_chars),
        }
        for row in rows
    ]


async def fetch_comment_candidates_all(
    *,
    limit: int,
    lookback_days: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"days": int(lookback_days)}
    limit_clause = ""
    if limit > 0:
        limit_clause = "LIMIT :limit"
        params["limit"] = int(limit)

    core_sql = f"""
        SELECT c.id,
               c.body,
               c.subreddit,
               c.score,
               c.source,
               c.source_post_id,
               p.title AS post_title,
               cs.value_score,
               cs.business_pool
        FROM comments c
        JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
        JOIN posts_raw p
          ON p.source = c.source
         AND p.source_post_id = c.source_post_id
         AND p.is_current = TRUE
        LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
        WHERE cs.business_pool IN ('core','lab')
          AND c.created_utc >= NOW() - (:days * INTERVAL '1 day')
          AND llm.comment_id IS NULL
        ORDER BY cs.value_score DESC, c.score DESC
        {limit_clause}
    """

    async with SessionFactory() as session:
        result = await session.execute(sqltext(core_sql), params)
        rows = [dict(row) for row in result.mappings().all()]

        if include_noise and noise_ratio > 0:
            base_count = int(limit) if limit > 0 else await count_comment_candidates_core_lab(
                session=session,
                lookback_days=lookback_days,
            )
            noise_limit = int(base_count * noise_ratio)
            if noise_limit > 0:
                noise_params = {
                    "days": int(lookback_days),
                    "min_score": int(noise_min_score),
                    "limit": int(noise_limit),
                }
                noise_sql = """
                    SELECT c.id,
                           c.body,
                           c.subreddit,
                           c.score,
                           c.source,
                           c.source_post_id,
                           p.title AS post_title,
                           cs.value_score,
                           cs.business_pool
                    FROM comments c
                    JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                    JOIN posts_raw p
                      ON p.source = c.source
                     AND p.source_post_id = c.source_post_id
                     AND p.is_current = TRUE
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
                    WHERE cs.business_pool = 'noise'
                      AND c.created_utc >= NOW() - (:days * INTERVAL '1 day')
                      AND llm.comment_id IS NULL
                      AND c.score >= :min_score
                    ORDER BY c.score DESC
                    LIMIT :limit
                """
                noise_result = await session.execute(sqltext(noise_sql), noise_params)
                rows.extend(dict(row) for row in noise_result.mappings().all())
        return rows


async def count_comment_candidates_core_lab(
    *,
    session: Any,
    lookback_days: int,
) -> int:
    result = await session.execute(
        sqltext(
            """
            SELECT COUNT(*)
            FROM comments c
            JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
            JOIN posts_raw p
              ON p.source = c.source
             AND p.source_post_id = c.source_post_id
             AND p.is_current = TRUE
            LEFT JOIN comment_llm_labels llm ON llm.comment_id = c.id
            WHERE cs.business_pool IN ('core','lab')
              AND c.created_utc >= NOW() - (:days * INTERVAL '1 day')
              AND llm.comment_id IS NULL
            """
        ),
        {"days": int(lookback_days)},
    )
    return int(result.scalar_one())


def build_comment_activation_export(
    *,
    rows: list[dict[str, Any]],
    max_body_chars: int,
    effective_domain_weights: dict[str, int],
    target_total: int,
    base_quota: int,
    first_batch_size: int,
    batch_size: int,
) -> tuple[list[list[dict[str, Any]]], dict[str, Any]]:
    plan = build_comment_activation_export_plan(
        rows=rows,
        max_body_chars=max_body_chars,
        effective_domain_weights=effective_domain_weights,
        target_total=target_total,
        base_quota=base_quota,
        first_batch_size=first_batch_size,
        batch_size=batch_size,
    )
    return plan.payload_batches(), plan.summary


def export_comment_activation(
    *,
    lookback_days: int,
    max_body_chars: int,
    target_total: int,
    base_quota: int,
    first_batch_size: int,
    batch_size: int,
) -> tuple[list[list[dict[str, Any]]], dict[str, Any]]:
    plan = run_coro(
        build_historical_comment_activation_plan(
            lookback_days=lookback_days,
            max_body_chars=max_body_chars,
            target_total=target_total,
            base_quota=base_quota,
            first_batch_size=first_batch_size,
            batch_size=batch_size,
        )
    )
    if plan is None:
        return [], {}
    return plan.payload_batches(), plan.summary


def export_comments_all(
    *,
    limit: int,
    lookback_days: int,
    max_body_chars: int,
    include_noise: bool,
    noise_ratio: float,
    noise_min_score: int,
) -> list[dict[str, Any]]:
    rows = run_coro(
        fetch_comment_candidates_all(
            limit=limit,
            lookback_days=lookback_days,
            include_noise=include_noise,
            noise_ratio=noise_ratio,
            noise_min_score=noise_min_score,
        )
    ) or []
    return [
        comment_payload_from_row(row, max_body_chars=max_body_chars)
        for row in rows
    ]


__all__ = [
    "build_comment_activation_export",
    "count_comment_candidates_core_lab",
    "export_comment_activation",
    "export_comments",
    "export_comments_all",
    "fetch_comment_candidates_all",
]
