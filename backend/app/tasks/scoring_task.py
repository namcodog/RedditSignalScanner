from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.utils.asyncio_runner import run as run_coro

logger = logging.getLogger(__name__)


def _bucket_score(score: int, num_comments: int) -> tuple[float, str]:
    """Simple heuristic scoring to keep pipeline flowing."""
    if score >= 50 or num_comments >= 50:
        return 8.0, "core"
    if score >= 10 or num_comments >= 5:
        return 6.0, "core"
    if score >= 3 or num_comments >= 1:
        return 3.0, "lab"
    return 1.0, "noise"


async def _score_new_posts(limit: int = 500) -> dict[str, Any]:
    """Insert default rulebook_v1 scores for unscored posts."""
    processed = 0
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, score, num_comments
                FROM posts_raw
                WHERE is_current = TRUE
                  AND NOT EXISTS (
                      SELECT 1 FROM post_scores ps
                      WHERE ps.post_id = posts_raw.id
                        AND ps.is_latest = TRUE
                  )
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        posts = [(int(r.id), int(r.score or 0), int(r.num_comments or 0)) for r in rows]
        if not posts:
            return {"processed": 0}

        now = datetime.now(timezone.utc)
        for pid, score, num_comments in posts:
            value_score, pool = _bucket_score(score, num_comments)
            await session.execute(
                text(
                    """
                    INSERT INTO post_scores (
                        post_id, llm_version, rule_version, scored_at,
                        is_latest, value_score, opportunity_score,
                        business_pool, sentiment, purchase_intent_score,
                        tags_analysis, entities_extracted, calculation_log
                    ) VALUES (
                        :post_id, :llm_version, :rule_version, :scored_at,
                        TRUE, :value_score, NULL,
                        :business_pool, NULL, NULL,
                        '{}'::jsonb, '[]'::jsonb, '{}'::jsonb
                    )
                    ON CONFLICT (post_id) WHERE is_latest = TRUE DO NOTHING
                    """
                ),
                {
                    "post_id": pid,
                    "llm_version": "none",
                    "rule_version": "rulebook_v1",
                    "scored_at": now,
                    "value_score": value_score,
                    "business_pool": pool,
                },
            )
            processed += 1
        await session.commit()
    return {"processed": processed}


async def _score_new_comments(limit: int = 500) -> dict[str, Any]:
    """Insert default rulebook_v1 scores for unscored comments."""
    processed = 0
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, score
                FROM comments
                WHERE source = 'reddit'
                  AND body IS NOT NULL
                  AND LENGTH(body) > 20
                  AND COALESCE(removed_by_category, '') NOT IN ('deleted', 'removed')
                  AND NOT EXISTS (
                      SELECT 1 FROM comment_scores cs
                      WHERE cs.comment_id = comments.id
                        AND cs.is_latest = TRUE
                  )
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        comments = [(int(r.id), int(r.score or 0)) for r in rows]
        if not comments:
            return {"processed": 0}

        now = datetime.now(timezone.utc)
        for cid, score in comments:
            value_score, pool = _bucket_score(score, 0)
            await session.execute(
                text(
                    """
                    INSERT INTO comment_scores (
                        comment_id, llm_version, rule_version, scored_at,
                        is_latest, value_score, opportunity_score,
                        business_pool, sentiment, purchase_intent_score,
                        tags_analysis, entities_extracted, calculation_log
                    ) VALUES (
                        :comment_id, :llm_version, :rule_version, :scored_at,
                        TRUE, :value_score, NULL,
                        :business_pool, NULL, NULL,
                        '{}'::jsonb, '[]'::jsonb, '{}'::jsonb
                    )
                    ON CONFLICT (comment_id) WHERE is_latest = TRUE DO NOTHING
                    """
                ),
                {
                    "comment_id": cid,
                    "llm_version": "none",
                    "rule_version": "rulebook_v1",
                    "scored_at": now,
                    "value_score": value_score,
                    "business_pool": pool,
                },
            )
            processed += 1
        await session.commit()
    return {"processed": processed}


@celery_app.task(name="tasks.analysis.score_new_posts_v1")  # type: ignore[misc]
def score_new_posts_v1(limit: int = 500) -> dict[str, Any]:
    """Backfill default scores for newly ingested posts."""

    async def _run() -> dict[str, Any]:
        return await _score_new_posts(limit=limit)

    result = run_coro(_run())
    logger.info("score_new_posts_v1 processed=%s", result.get("processed"))
    return result


@celery_app.task(name="tasks.analysis.score_new_comments_v1")  # type: ignore[misc]
def score_new_comments_v1(limit: int = 500) -> dict[str, Any]:
    """Backfill default scores for newly ingested comments."""

    async def _run() -> dict[str, Any]:
        return await _score_new_comments(limit=limit)

    result = run_coro(_run())
    logger.info("score_new_comments_v1 processed=%s", result.get("processed"))
    return result
