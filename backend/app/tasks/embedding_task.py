from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy import text as sqltext

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.services.semantic.embedding_service import MODEL_NAME, embedding_service
from app.utils.asyncio_runner import run as run_coro

logger = logging.getLogger(__name__)

DEFAULT_BATCH_LIMIT = 200
DEFAULT_MAX_CHARS = 2000
DEFAULT_EMBED_BATCH_SIZE = 64
DEFAULT_COMMENT_MAX_CHARS = 1200
DEFAULT_COMMENT_LONG_TAIL_RATIO = 0.2
DEFAULT_COMMENT_LOOKBACK_DAYS = 365
DEFAULT_COMMENT_HIGH_SCORE = 7
DEFAULT_COMMENT_LOW_SCORE = 2
DEFAULT_COMMENT_FALLBACK_HIGH_SCORE = 10
DEFAULT_COMMENT_FALLBACK_LOW_SCORE = 2
DEFAULT_COMMENT_FALLBACK_LOW_MAX = 9
MODEL_VERSION = MODEL_NAME
FEATURE_VERSION = 1


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "..."


async def _fetch_missing_posts(limit: int) -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        result = await session.execute(
            sqltext(
                """
                SELECT p.id, p.title, p.body
                FROM posts_raw p
                LEFT JOIN post_embeddings pe ON pe.post_id = p.id
                WHERE p.is_current = true
                  AND pe.post_id IS NULL
                LIMIT :limit
                """
            ),
            {"limit": int(limit)},
        )
        return [dict(row) for row in result.mappings().all()]

async def _fetch_missing_comments(
    *, limit: int, long_tail_ratio: float, lookback_days: int
) -> list[dict[str, Any]]:
    desired_high = int(limit * (1 - long_tail_ratio))
    high_limit = max(1, desired_high) if limit > 0 else 0
    tail_limit = max(0, int(limit) - high_limit)

    async with SessionFactory() as session:
        high_rows = await session.execute(
            sqltext(
                """
                SELECT c.id, c.body
                FROM comments c
                JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                LEFT JOIN comment_embeddings ce ON ce.comment_id = c.id
                WHERE ce.comment_id IS NULL
                  AND c.created_utc >= (NOW() - (:lookback_days * INTERVAL '1 day'))
                  AND cs.business_pool IN ('core', 'lab')
                  AND (
                    cs.value_score >= :high_score
                    OR (cs.value_score IS NULL AND c.score >= :fallback_high_score)
                  )
                  AND c.body IS NOT NULL
                  AND length(btrim(c.body)) > 0
                ORDER BY cs.value_score DESC NULLS LAST, c.score DESC
                LIMIT :limit
                """
            ),
            {
                "limit": int(high_limit),
                "lookback_days": int(lookback_days),
                "high_score": float(DEFAULT_COMMENT_HIGH_SCORE),
                "fallback_high_score": int(DEFAULT_COMMENT_FALLBACK_HIGH_SCORE),
            },
        )
        rows = [dict(row) for row in high_rows.mappings().all()]
        if len(rows) < desired_high:
            tail_limit += (desired_high - len(rows))

        if tail_limit <= 0:
            return rows

        tail_rows = await session.execute(
            sqltext(
                """
                SELECT c.id, c.body
                FROM comments c
                JOIN comment_scores_latest_v cs ON cs.comment_id = c.id
                LEFT JOIN comment_embeddings ce ON ce.comment_id = c.id
                WHERE ce.comment_id IS NULL
                  AND c.created_utc >= (NOW() - (:lookback_days * INTERVAL '1 day'))
                  AND cs.business_pool IN ('core', 'lab')
                  AND (
                    (cs.value_score >= :low_score AND cs.value_score < :high_score)
                    OR (cs.value_score IS NULL AND c.score BETWEEN :fallback_low_score AND :fallback_low_max)
                  )
                  AND c.body IS NOT NULL
                  AND length(btrim(c.body)) > 0
                ORDER BY random()
                LIMIT :limit
                """
            ),
            {
                "limit": int(tail_limit),
                "lookback_days": int(lookback_days),
                "low_score": float(DEFAULT_COMMENT_LOW_SCORE),
                "high_score": float(DEFAULT_COMMENT_HIGH_SCORE),
                "fallback_low_score": int(DEFAULT_COMMENT_FALLBACK_LOW_SCORE),
                "fallback_low_max": int(DEFAULT_COMMENT_FALLBACK_LOW_MAX),
            },
        )
        rows.extend(dict(row) for row in tail_rows.mappings().all())
        return rows

async def _backfill_posts_batch(
    *, limit: int, max_chars: int
) -> Dict[str, Any]:
    rows = await _fetch_missing_posts(limit)
    if not rows:
        return {"processed": 0, "status": "empty"}

    ids: list[int] = []
    texts: list[str] = []
    for row in rows:
        content = f"{row.get('title') or ''}\n{row.get('body') or ''}".strip()
        ids.append(int(row["id"]))
        texts.append(_truncate(content, max_chars))

    batch_size = min(DEFAULT_EMBED_BATCH_SIZE, len(texts))
    embeddings = embedding_service.encode(texts, batch_size=batch_size)

    insert_rows = []
    for post_id, vec in zip(ids, embeddings):
        insert_rows.append(
            {
                "post_id": post_id,
                "model_version": MODEL_VERSION,
                "embedding": str(vec),
                "source_model": MODEL_VERSION,
                "feature_version": FEATURE_VERSION,
            }
        )

    async with SessionFactory() as session:
        await session.execute(
            sqltext(
                """
                INSERT INTO post_embeddings (
                    post_id,
                    model_version,
                    embedding,
                    source_model,
                    feature_version
                )
                VALUES (
                    :post_id,
                    :model_version,
                    :embedding,
                    :source_model,
                    :feature_version
                )
                ON CONFLICT (post_id, model_version) DO NOTHING
                """
            ),
            insert_rows,
        )
        await session.commit()

    return {"processed": len(rows), "status": "ok"}

async def _backfill_comments_batch(
    *, limit: int, max_chars: int
) -> Dict[str, Any]:
    rows = await _fetch_missing_comments(
        limit=limit,
        long_tail_ratio=DEFAULT_COMMENT_LONG_TAIL_RATIO,
        lookback_days=DEFAULT_COMMENT_LOOKBACK_DAYS,
    )
    if not rows:
        return {"processed": 0, "status": "empty"}

    ids: list[int] = []
    texts: list[str] = []
    for row in rows:
        ids.append(int(row["id"]))
        texts.append(_truncate(row.get("body") or "", max_chars))

    batch_size = min(DEFAULT_EMBED_BATCH_SIZE, len(texts))
    embeddings = embedding_service.encode(texts, batch_size=batch_size)

    insert_rows = []
    for comment_id, vec in zip(ids, embeddings):
        insert_rows.append(
            {
                "comment_id": comment_id,
                "model_version": MODEL_VERSION,
                "embedding": str(vec),
                "source_model": MODEL_VERSION,
                "feature_version": FEATURE_VERSION,
            }
        )

    async with SessionFactory() as session:
        await session.execute(
            sqltext(
                """
                INSERT INTO comment_embeddings (
                    comment_id,
                    model_version,
                    embedding,
                    source_model,
                    feature_version
                )
                VALUES (
                    :comment_id,
                    :model_version,
                    :embedding,
                    :source_model,
                    :feature_version
                )
                ON CONFLICT (comment_id, model_version) DO NOTHING
                """
            ),
            insert_rows,
        )
        await session.commit()

    return {"processed": len(rows), "status": "ok"}

def run_backfill_posts_full(
    *, limit: int = DEFAULT_BATCH_LIMIT, max_batches: int | None = None
) -> Dict[str, Any]:
    total_processed = 0
    batches = 0
    while True:
        result = run_coro(_backfill_posts_batch(limit=limit, max_chars=DEFAULT_MAX_CHARS))
        processed = int(result.get("processed") or 0)
        total_processed += processed
        batches += 1
        if processed == 0:
            return {
                "processed": total_processed,
                "batches": batches,
                "status": "complete",
            }
        if max_batches is not None and batches >= max_batches:
            return {
                "processed": total_processed,
                "batches": batches,
                "status": "partial",
            }


def run_backfill_comments_full(
    *, limit: int = DEFAULT_BATCH_LIMIT, max_batches: int | None = None
) -> Dict[str, Any]:
    total_processed = 0
    batches = 0
    while True:
        result = run_coro(
            _backfill_comments_batch(limit=limit, max_chars=DEFAULT_COMMENT_MAX_CHARS)
        )
        processed = int(result.get("processed") or 0)
        total_processed += processed
        batches += 1
        if processed == 0:
            return {
                "processed": total_processed,
                "batches": batches,
                "status": "complete",
            }
        if max_batches is not None and batches >= max_batches:
            return {
                "processed": total_processed,
                "batches": batches,
                "status": "partial",
            }


@celery_app.task(name="tasks.embedding.backfill_posts_batch")  # type: ignore[misc]
def backfill_posts_batch(limit: int | None = None) -> Dict[str, Any]:
    limit_value = int(limit or DEFAULT_BATCH_LIMIT)
    result = run_coro(_backfill_posts_batch(limit=limit_value, max_chars=DEFAULT_MAX_CHARS))
    logger.info("backfill_posts_batch processed=%s", result.get("processed"))
    return result


@celery_app.task(name="tasks.embedding.backfill_posts_full")  # type: ignore[misc]
def backfill_posts_full(
    limit: int | None = None, max_batches: int | None = None
) -> Dict[str, Any]:
    limit_value = int(limit or DEFAULT_BATCH_LIMIT)
    result = run_backfill_posts_full(limit=limit_value, max_batches=max_batches)
    logger.info("backfill_posts_full processed=%s", result.get("processed"))
    return result


@celery_app.task(name="tasks.embedding.backfill_comments_batch")  # type: ignore[misc]
def backfill_comments_batch(limit: int | None = None) -> Dict[str, Any]:
    limit_value = int(limit or DEFAULT_BATCH_LIMIT)
    result = run_coro(
        _backfill_comments_batch(limit=limit_value, max_chars=DEFAULT_COMMENT_MAX_CHARS)
    )
    logger.info("backfill_comments_batch processed=%s", result.get("processed"))
    return result


@celery_app.task(name="tasks.embedding.backfill_comments_full")  # type: ignore[misc]
def backfill_comments_full(
    limit: int | None = None, max_batches: int | None = None
) -> Dict[str, Any]:
    limit_value = int(limit or DEFAULT_BATCH_LIMIT)
    result = run_backfill_comments_full(limit=limit_value, max_batches=max_batches)
    logger.info("backfill_comments_full processed=%s", result.get("processed"))
    return result


__all__ = [
    "backfill_posts_batch",
    "backfill_posts_full",
    "run_backfill_posts_full",
    "backfill_comments_batch",
    "backfill_comments_full",
    "run_backfill_comments_full",
]
