from __future__ import annotations

import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text as sqltext

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.llm.labeling import LLMLabeler
from app.services.semantic.llm_term_sync import sync_llm_terms
from app.utils.asyncio_runner import run as run_coro

logger = logging.getLogger(__name__)

_LAB_LONG_SAMPLE_RATE = 0.15
_MID_SCORE_MIN = 5.0
_MID_SCORE_MAX = 7.0
_HIGH_SCORE_MIN = 9.0
_LOW_SCORE_MAX = 2.0
_HIGH_SCORE_RATIO = 0.3
_LAB_BODY_RATIO = 0.6
_LAB_COMMENT_RATIO = 0.6
_LLM_BATCH_SIZE = 2


def _chunk_items(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]

def _json_sanitize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _json_sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_sanitize(v) for v in value]
    return value


def _should_use_long_lab(row_id: int, value_score: float) -> bool:
    if _MID_SCORE_MIN <= value_score <= _MID_SCORE_MAX:
        return True
    bucket = abs(int(row_id)) % 100
    return bucket < int(_LAB_LONG_SAMPLE_RATE * 100)


def _split_limits(limit: int, high_ratio: float) -> tuple[int, int]:
    if limit <= 0:
        return 0, 0
    high_limit = int(round(limit * high_ratio))
    high_limit = min(limit, max(0, high_limit))
    mid_limit = max(0, limit - high_limit)
    return mid_limit, high_limit


async def _fetch_post_candidates(limit: int, lookback_days: int) -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        mid_limit, high_limit = _split_limits(limit, _HIGH_SCORE_RATIO)
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
                    "low_score": _LOW_SCORE_MAX,
                    "high_score": _HIGH_SCORE_MIN,
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
                    "high_score": _HIGH_SCORE_MIN,
                },
            )
            for row in result.mappings().all():
                post_id = int(row["id"])
                if post_id in seen:
                    continue
                seen.add(post_id)
                rows.append(row)

        return rows


async def _fetch_comment_candidates(limit: int, lookback_days: int) -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        mid_limit, high_limit = _split_limits(limit, _HIGH_SCORE_RATIO)
        rows: list[dict[str, Any]] = []
        seen: set[int] = set()
        base_params = {"days": int(lookback_days)}

        if mid_limit > 0:
            result = await session.execute(
                sqltext(
                    """
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
                      AND cs.value_score > :low_score
                      AND cs.value_score < :high_score
                    ORDER BY cs.value_score DESC, c.score DESC
                    LIMIT :limit
                    """
                ),
                {
                    **base_params,
                    "limit": int(mid_limit),
                    "low_score": _LOW_SCORE_MAX,
                    "high_score": _HIGH_SCORE_MIN,
                },
            )
            for row in result.mappings().all():
                comment_id = int(row["id"])
                if comment_id in seen:
                    continue
                seen.add(comment_id)
                rows.append(row)

        if high_limit > 0:
            result = await session.execute(
                sqltext(
                    """
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
                      AND cs.value_score >= :high_score
                    ORDER BY cs.value_score DESC, c.score DESC
                    LIMIT :limit
                    """
                ),
                {
                    **base_params,
                    "limit": int(high_limit),
                    "high_score": _HIGH_SCORE_MIN,
                },
            )
            for row in result.mappings().all():
                comment_id = int(row["id"])
                if comment_id in seen:
                    continue
                seen.add(comment_id)
                rows.append(row)

        return rows


async def _fetch_top_comments(
    source: str, source_post_id: str, limit: int
) -> list[str]:
    async with SessionFactory() as session:
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
        return [str(r.body or "") for r in rows]


async def _upsert_post_label(
    *,
    session,
    post_id: int,
    text_norm_hash: str | None,
    llm_version: str,
    model_name: str,
    prompt_version: str,
    analysis: dict[str, Any],
    score: dict[str, Any],
    input_chars: int,
    output_chars: int,
) -> None:
    await session.execute(
        sqltext(
            """
            INSERT INTO post_llm_labels (
                post_id,
                text_norm_hash,
                llm_version,
                model_name,
                prompt_version,
                value_score,
                opportunity_score,
                business_pool,
                sentiment,
                purchase_intent_score,
                tags_analysis,
                entities_extracted,
                input_chars,
                output_chars,
                updated_at
            ) VALUES (
                :post_id,
                :text_norm_hash,
                :llm_version,
                :model_name,
                :prompt_version,
                :value_score,
                :opportunity_score,
                :business_pool,
                :sentiment,
                :purchase_intent_score,
                CAST(:tags_analysis AS jsonb),
                CAST(:entities_extracted AS jsonb),
                :input_chars,
                :output_chars,
                NOW()
            )
            ON CONFLICT (post_id) DO UPDATE
            SET text_norm_hash = EXCLUDED.text_norm_hash,
                llm_version = EXCLUDED.llm_version,
                model_name = EXCLUDED.model_name,
                prompt_version = EXCLUDED.prompt_version,
                value_score = EXCLUDED.value_score,
                opportunity_score = EXCLUDED.opportunity_score,
                business_pool = EXCLUDED.business_pool,
                sentiment = EXCLUDED.sentiment,
                purchase_intent_score = EXCLUDED.purchase_intent_score,
                tags_analysis = EXCLUDED.tags_analysis,
                entities_extracted = EXCLUDED.entities_extracted,
                input_chars = EXCLUDED.input_chars,
                output_chars = EXCLUDED.output_chars,
                updated_at = NOW()
            """
        ),
        {
            "post_id": int(post_id),
            "text_norm_hash": text_norm_hash,
            "llm_version": llm_version,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "value_score": score.get("value_score"),
            "opportunity_score": score.get("opportunity_score"),
            "business_pool": score.get("business_pool"),
            "sentiment": analysis.get("sentiment"),
            "purchase_intent_score": analysis.get("purchase_intent_score"),
            "tags_analysis": json.dumps(analysis),
            "entities_extracted": json.dumps(analysis.get("entities") or {}),
            "input_chars": int(input_chars),
            "output_chars": int(output_chars),
        },
    )


async def _upsert_comment_label(
    *,
    session,
    comment_id: int,
    llm_version: str,
    model_name: str,
    prompt_version: str,
    analysis: dict[str, Any],
    score: dict[str, Any],
    input_chars: int,
    output_chars: int,
) -> None:
    await session.execute(
        sqltext(
            """
            INSERT INTO comment_llm_labels (
                comment_id,
                llm_version,
                model_name,
                prompt_version,
                value_score,
                opportunity_score,
                business_pool,
                sentiment,
                purchase_intent_score,
                tags_analysis,
                entities_extracted,
                input_chars,
                output_chars,
                updated_at
            ) VALUES (
                :comment_id,
                :llm_version,
                :model_name,
                :prompt_version,
                :value_score,
                :opportunity_score,
                :business_pool,
                :sentiment,
                :purchase_intent_score,
                CAST(:tags_analysis AS jsonb),
                CAST(:entities_extracted AS jsonb),
                :input_chars,
                :output_chars,
                NOW()
            )
            ON CONFLICT (comment_id) DO UPDATE
            SET llm_version = EXCLUDED.llm_version,
                model_name = EXCLUDED.model_name,
                prompt_version = EXCLUDED.prompt_version,
                value_score = EXCLUDED.value_score,
                opportunity_score = EXCLUDED.opportunity_score,
                business_pool = EXCLUDED.business_pool,
                sentiment = EXCLUDED.sentiment,
                purchase_intent_score = EXCLUDED.purchase_intent_score,
                tags_analysis = EXCLUDED.tags_analysis,
                entities_extracted = EXCLUDED.entities_extracted,
                input_chars = EXCLUDED.input_chars,
                output_chars = EXCLUDED.output_chars,
                updated_at = NOW()
            """
        ),
        {
            "comment_id": int(comment_id),
            "llm_version": llm_version,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "value_score": score.get("value_score"),
            "opportunity_score": score.get("opportunity_score"),
            "business_pool": score.get("business_pool"),
            "sentiment": analysis.get("sentiment"),
            "purchase_intent_score": analysis.get("purchase_intent_score"),
            "tags_analysis": json.dumps(analysis),
            "entities_extracted": json.dumps(analysis.get("entities") or {}),
            "input_chars": int(input_chars),
            "output_chars": int(output_chars),
        },
    )


async def _label_posts_batch(limit: int, lookback_days: int) -> dict[str, Any]:
    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        return {"processed": 0, "status": "missing_api_key"}

    core_body_chars = int(settings.llm_label_body_chars)
    core_comment_chars = int(settings.llm_label_comment_chars)
    lab_body_chars = max(200, int(core_body_chars * _LAB_BODY_RATIO))
    lab_comment_chars = max(80, int(core_comment_chars * _LAB_COMMENT_RATIO))

    core_labeler = LLMLabeler(
        model=settings.llm_label_model_name,
        prompt_version=settings.llm_label_prompt_version,
        max_body_chars=core_body_chars,
        max_comment_chars=core_comment_chars,
        api_key=api_key,
    )
    lab_labeler = LLMLabeler(
        model=settings.llm_label_model_name,
        prompt_version=settings.llm_label_prompt_version,
        max_body_chars=lab_body_chars,
        max_comment_chars=lab_comment_chars,
        api_key=api_key,
    )
    candidates = await _fetch_post_candidates(limit=limit, lookback_days=lookback_days)
    if not candidates:
        return {"processed": 0, "status": "no_candidates"}

    processed = 0
    async with SessionFactory() as session:
        long_items: list[dict[str, Any]] = []
        short_items: list[dict[str, Any]] = []
        row_by_id: dict[int, dict[str, Any]] = {}

        for row in candidates:
            value_score = float(row.get("value_score") or 0.0)
            if value_score <= _LOW_SCORE_MAX:
                continue
            pool = str(row.get("business_pool") or "lab").lower()
            use_long = pool == "core"
            if pool == "lab":
                use_long = _should_use_long_lab(int(row["id"]), value_score)

            comment_limit = 2 if use_long else 1
            top_comments = await _fetch_top_comments(
                row["source"], row["source_post_id"], limit=comment_limit
            )
            item = {
                "id": int(row["id"]),
                "title": row.get("title") or "",
                "body": row.get("body") or "",
                "subreddit": row.get("subreddit") or "",
                "comments": top_comments,
            }
            row_by_id[int(row["id"])] = row
            if use_long:
                long_items.append(item)
            else:
                short_items.append(item)

        for batch in _chunk_items(long_items, _LLM_BATCH_SIZE):
            results = await core_labeler.label_posts_batch(items=batch)
            if not results:
                for item in batch:
                    try:
                        analysis, score, in_chars, out_chars = await core_labeler.label_post(
                            title=str(item.get("title") or ""),
                            body=str(item.get("body") or ""),
                            subreddit=str(item.get("subreddit") or ""),
                            comments=item.get("comments") or [],
                        )
                        await _upsert_post_label(
                            session=session,
                            post_id=int(item["id"]),
                            text_norm_hash=row_by_id[int(item["id"])].get("text_norm_hash"),
                            llm_version=settings.llm_label_prompt_version,
                            model_name=core_labeler.model_name,
                            prompt_version=core_labeler.prompt_version,
                            analysis=analysis,
                            score=score.__dict__,
                            input_chars=in_chars,
                            output_chars=out_chars,
                        )
                        await sync_llm_terms(
                            session,
                            analysis=analysis,
                            llm_version=settings.llm_label_prompt_version,
                            prompt_version=core_labeler.prompt_version,
                        )
                        processed += 1
                    except Exception:
                        await session.rollback()
                        continue
                await session.commit()
                continue
            for result in results:
                try:
                    row = row_by_id.get(int(result["id"]))
                    if not row:
                        continue
                    await _upsert_post_label(
                        session=session,
                        post_id=int(result["id"]),
                        text_norm_hash=row.get("text_norm_hash"),
                        llm_version=settings.llm_label_prompt_version,
                        model_name=core_labeler.model_name,
                        prompt_version=core_labeler.prompt_version,
                        analysis=result["analysis"],
                        score=result["score"].__dict__,
                        input_chars=int(result["input_chars"]),
                        output_chars=int(result["output_chars"]),
                    )
                    await sync_llm_terms(
                        session,
                        analysis=result["analysis"],
                        llm_version=settings.llm_label_prompt_version,
                        prompt_version=core_labeler.prompt_version,
                    )
                    processed += 1
                except Exception:
                    await session.rollback()
                    continue
            await session.commit()

        for batch in _chunk_items(short_items, _LLM_BATCH_SIZE):
            results = await lab_labeler.label_posts_batch(items=batch)
            if not results:
                for item in batch:
                    try:
                        analysis, score, in_chars, out_chars = await lab_labeler.label_post(
                            title=str(item.get("title") or ""),
                            body=str(item.get("body") or ""),
                            subreddit=str(item.get("subreddit") or ""),
                            comments=item.get("comments") or [],
                        )
                        await _upsert_post_label(
                            session=session,
                            post_id=int(item["id"]),
                            text_norm_hash=row_by_id[int(item["id"])].get("text_norm_hash"),
                            llm_version=settings.llm_label_prompt_version,
                            model_name=lab_labeler.model_name,
                            prompt_version=lab_labeler.prompt_version,
                            analysis=analysis,
                            score=score.__dict__,
                            input_chars=in_chars,
                            output_chars=out_chars,
                        )
                        await sync_llm_terms(
                            session,
                            analysis=analysis,
                            llm_version=settings.llm_label_prompt_version,
                            prompt_version=lab_labeler.prompt_version,
                        )
                        processed += 1
                    except Exception:
                        await session.rollback()
                        continue
                await session.commit()
                continue
            for result in results:
                try:
                    row = row_by_id.get(int(result["id"]))
                    if not row:
                        continue
                    await _upsert_post_label(
                        session=session,
                        post_id=int(result["id"]),
                        text_norm_hash=row.get("text_norm_hash"),
                        llm_version=settings.llm_label_prompt_version,
                        model_name=lab_labeler.model_name,
                        prompt_version=lab_labeler.prompt_version,
                        analysis=result["analysis"],
                        score=result["score"].__dict__,
                        input_chars=int(result["input_chars"]),
                        output_chars=int(result["output_chars"]),
                    )
                    await sync_llm_terms(
                        session,
                        analysis=result["analysis"],
                        llm_version=settings.llm_label_prompt_version,
                        prompt_version=lab_labeler.prompt_version,
                    )
                    processed += 1
                except Exception:
                    await session.rollback()
                    continue
            await session.commit()

    return {"processed": processed, "status": "ok"}


async def _label_comments_batch(limit: int, lookback_days: int) -> dict[str, Any]:
    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        return {"processed": 0, "status": "missing_api_key"}

    core_body_chars = int(settings.llm_label_body_chars)
    core_comment_chars = int(settings.llm_label_comment_chars)
    lab_body_chars = max(160, int(core_body_chars * _LAB_BODY_RATIO))
    lab_comment_chars = max(80, int(core_comment_chars * _LAB_COMMENT_RATIO))

    core_labeler = LLMLabeler(
        model=settings.llm_label_model_name,
        prompt_version=settings.llm_label_prompt_version,
        max_body_chars=core_body_chars,
        max_comment_chars=core_comment_chars,
        api_key=api_key,
    )
    lab_labeler = LLMLabeler(
        model=settings.llm_label_model_name,
        prompt_version=settings.llm_label_prompt_version,
        max_body_chars=lab_body_chars,
        max_comment_chars=lab_comment_chars,
        api_key=api_key,
    )
    candidates = await _fetch_comment_candidates(
        limit=limit, lookback_days=lookback_days
    )
    if not candidates:
        return {"processed": 0, "status": "no_candidates"}

    processed = 0
    async with SessionFactory() as session:
        long_items: list[dict[str, Any]] = []
        short_items: list[dict[str, Any]] = []
        row_by_id: dict[int, dict[str, Any]] = {}

        for row in candidates:
            value_score = float(row.get("value_score") or 0.0)
            if value_score <= _LOW_SCORE_MAX:
                continue
            pool = str(row.get("business_pool") or "lab").lower()
            use_long = pool == "core"
            if pool == "lab":
                use_long = _should_use_long_lab(int(row["id"]), value_score)

            item = {
                "id": int(row["id"]),
                "body": row.get("body") or "",
                "post_title": row.get("post_title") or "",
                "subreddit": row.get("subreddit") or "",
            }
            row_by_id[int(row["id"])] = row
            if use_long:
                long_items.append(item)
            else:
                short_items.append(item)

        for batch in _chunk_items(long_items, _LLM_BATCH_SIZE):
            results = await core_labeler.label_comments_batch(items=batch)
            if not results:
                for item in batch:
                    try:
                        analysis, score, in_chars, out_chars = await core_labeler.label_comment(
                            body=str(item.get("body") or ""),
                            post_title=str(item.get("post_title") or ""),
                            subreddit=str(item.get("subreddit") or ""),
                        )
                        await _upsert_comment_label(
                            session=session,
                            comment_id=int(item["id"]),
                            llm_version=settings.llm_label_prompt_version,
                            model_name=core_labeler.model_name,
                            prompt_version=core_labeler.prompt_version,
                            analysis=analysis,
                            score=score.__dict__,
                            input_chars=in_chars,
                            output_chars=out_chars,
                        )
                        await sync_llm_terms(
                            session,
                            analysis=analysis,
                            llm_version=settings.llm_label_prompt_version,
                            prompt_version=core_labeler.prompt_version,
                        )
                        processed += 1
                    except Exception:
                        await session.rollback()
                        continue
                await session.commit()
                continue
            for result in results:
                try:
                    row = row_by_id.get(int(result["id"]))
                    if not row:
                        continue
                    await _upsert_comment_label(
                        session=session,
                        comment_id=int(result["id"]),
                        llm_version=settings.llm_label_prompt_version,
                        model_name=core_labeler.model_name,
                        prompt_version=core_labeler.prompt_version,
                        analysis=result["analysis"],
                        score=result["score"].__dict__,
                        input_chars=int(result["input_chars"]),
                        output_chars=int(result["output_chars"]),
                    )
                    await sync_llm_terms(
                        session,
                        analysis=result["analysis"],
                        llm_version=settings.llm_label_prompt_version,
                        prompt_version=core_labeler.prompt_version,
                    )
                    processed += 1
                except Exception:
                    await session.rollback()
                    continue
            await session.commit()

        for batch in _chunk_items(short_items, _LLM_BATCH_SIZE):
            results = await lab_labeler.label_comments_batch(items=batch)
            if not results:
                for item in batch:
                    try:
                        analysis, score, in_chars, out_chars = await lab_labeler.label_comment(
                            body=str(item.get("body") or ""),
                            post_title=str(item.get("post_title") or ""),
                            subreddit=str(item.get("subreddit") or ""),
                        )
                        await _upsert_comment_label(
                            session=session,
                            comment_id=int(item["id"]),
                            llm_version=settings.llm_label_prompt_version,
                            model_name=lab_labeler.model_name,
                            prompt_version=lab_labeler.prompt_version,
                            analysis=analysis,
                            score=score.__dict__,
                            input_chars=in_chars,
                            output_chars=out_chars,
                        )
                        await sync_llm_terms(
                            session,
                            analysis=analysis,
                            llm_version=settings.llm_label_prompt_version,
                            prompt_version=lab_labeler.prompt_version,
                        )
                        processed += 1
                    except Exception:
                        await session.rollback()
                        continue
                await session.commit()
                continue
            for result in results:
                try:
                    row = row_by_id.get(int(result["id"]))
                    if not row:
                        continue
                    await _upsert_comment_label(
                        session=session,
                        comment_id=int(result["id"]),
                        llm_version=settings.llm_label_prompt_version,
                        model_name=lab_labeler.model_name,
                        prompt_version=lab_labeler.prompt_version,
                        analysis=result["analysis"],
                        score=result["score"].__dict__,
                        input_chars=int(result["input_chars"]),
                        output_chars=int(result["output_chars"]),
                    )
                    await sync_llm_terms(
                        session,
                        analysis=result["analysis"],
                        llm_version=settings.llm_label_prompt_version,
                        prompt_version=lab_labeler.prompt_version,
                    )
                    processed += 1
                except Exception:
                    await session.rollback()
                    continue
            await session.commit()

    return {"processed": processed, "status": "ok"}


async def _backfill_legacy_labels(limit: int) -> dict[str, Any]:
    processed = 0
    post_processed = 0
    comment_processed = 0
    async with SessionFactory() as session:
        rows = await session.execute(
            sqltext(
                """
                WITH latest_scores AS (
                    SELECT DISTINCT ON (ps.post_id)
                           ps.post_id,
                           ps.llm_version,
                           ps.tags_analysis,
                           ps.entities_extracted,
                           ps.value_score,
                           ps.opportunity_score,
                           ps.business_pool,
                           ps.sentiment,
                           ps.purchase_intent_score,
                           ps.scored_at,
                           p.text_norm_hash
                    FROM post_scores ps
                    JOIN posts_raw p ON p.id = ps.post_id
                    LEFT JOIN post_llm_labels llm ON llm.post_id = ps.post_id
                    LEFT JOIN post_llm_labels llm_hash
                      ON p.text_norm_hash IS NOT NULL
                     AND llm_hash.text_norm_hash = p.text_norm_hash
                    WHERE ps.llm_version IS NOT NULL
                      AND ps.llm_version <> 'none'
                      AND ps.tags_analysis <> '{}'::jsonb
                      AND llm.post_id IS NULL
                      AND llm_hash.post_id IS NULL
                    ORDER BY ps.post_id, ps.scored_at DESC NULLS LAST
                )
                SELECT *
                FROM latest_scores
                ORDER BY scored_at DESC NULLS LAST
                LIMIT :limit
                """
            ),
            {"limit": int(limit)},
        )
        for row in rows.mappings().all():
            analysis = dict(row.get("tags_analysis") or {})
            entities = row.get("entities_extracted") or {}
            if entities:
                analysis["entities"] = entities
            if row.get("sentiment") is not None:
                analysis["sentiment"] = row.get("sentiment")
            if row.get("purchase_intent_score") is not None:
                analysis["purchase_intent_score"] = row.get("purchase_intent_score")
            analysis = _json_sanitize(analysis)
            try:
                await _upsert_post_label(
                    session=session,
                    post_id=int(row["post_id"]),
                    text_norm_hash=row.get("text_norm_hash"),
                    llm_version=str(row.get("llm_version") or "legacy"),
                    model_name=str(row.get("llm_version") or "legacy"),
                    prompt_version="legacy_v2",
                    analysis=analysis,
                    score={
                        "value_score": row.get("value_score"),
                        "opportunity_score": row.get("opportunity_score"),
                        "business_pool": row.get("business_pool"),
                    },
                    input_chars=0,
                    output_chars=0,
                )
                try:
                    await sync_llm_terms(
                        session,
                        analysis=analysis,
                        llm_version=str(row.get("llm_version") or "legacy"),
                        prompt_version="legacy_v2",
                    )
                except Exception:
                    logger.warning(
                        "backfill_legacy_labels: sync_llm_terms failed for post_id=%s",
                        row.get("post_id"),
                    )
                processed += 1
                post_processed += 1
                if post_processed % 200 == 0:
                    await session.commit()
            except Exception:
                await session.rollback()
                continue
        # Commit post backfill separately so comment errors don't roll it back.
        await session.commit()
        comment_rows = await session.execute(
            sqltext(
                """
                WITH latest_scores AS (
                    SELECT DISTINCT ON (cs.comment_id)
                           cs.comment_id,
                           cs.llm_version,
                           cs.tags_analysis,
                           cs.entities_extracted,
                           cs.value_score,
                           cs.opportunity_score,
                           cs.business_pool,
                           cs.sentiment,
                           cs.purchase_intent_score,
                           cs.scored_at
                    FROM comment_scores cs
                    LEFT JOIN comment_llm_labels llm ON llm.comment_id = cs.comment_id
                    WHERE cs.llm_version IS NOT NULL
                      AND cs.llm_version <> 'none'
                      AND cs.tags_analysis <> '{}'::jsonb
                      AND llm.comment_id IS NULL
                    ORDER BY cs.comment_id, cs.scored_at DESC NULLS LAST
                )
                SELECT *
                FROM latest_scores
                ORDER BY scored_at DESC NULLS LAST
                LIMIT :limit
                """
            ),
            {"limit": int(limit)},
        )
        for row in comment_rows.mappings().all():
            analysis = dict(row.get("tags_analysis") or {})
            entities = row.get("entities_extracted") or {}
            if entities:
                analysis["entities"] = entities
            if row.get("sentiment") is not None:
                analysis["sentiment"] = row.get("sentiment")
            if row.get("purchase_intent_score") is not None:
                analysis["purchase_intent_score"] = row.get("purchase_intent_score")
            analysis = _json_sanitize(analysis)
            try:
                await _upsert_comment_label(
                    session=session,
                    comment_id=int(row["comment_id"]),
                    llm_version=str(row.get("llm_version") or "legacy"),
                    model_name=str(row.get("llm_version") or "legacy"),
                    prompt_version="legacy_v2",
                    analysis=analysis,
                    score={
                        "value_score": row.get("value_score"),
                        "opportunity_score": row.get("opportunity_score"),
                        "business_pool": row.get("business_pool"),
                    },
                    input_chars=0,
                    output_chars=0,
                )
                try:
                    await sync_llm_terms(
                        session,
                        analysis=analysis,
                        llm_version=str(row.get("llm_version") or "legacy"),
                        prompt_version="legacy_v2",
                    )
                except Exception:
                    logger.warning(
                        "backfill_legacy_labels: sync_llm_terms failed for comment_id=%s",
                        row.get("comment_id"),
                    )
                processed += 1
                comment_processed += 1
                if comment_processed % 200 == 0:
                    await session.commit()
            except Exception:
                await session.rollback()
                continue
        await session.commit()

    return {"processed": processed, "status": "ok"}


@celery_app.task(name="tasks.llm.label_posts_batch")  # type: ignore[misc]
def label_posts_batch(limit: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    limit_value = int(limit or settings.llm_label_post_limit)
    days = int(settings.llm_label_lookback_days)
    result = run_coro(_label_posts_batch(limit_value, days))
    logger.info("label_posts_batch processed=%s", result.get("processed"))
    return result


@celery_app.task(name="tasks.llm.label_comments_batch")  # type: ignore[misc]
def label_comments_batch(limit: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    limit_value = int(limit or settings.llm_label_comment_limit)
    days = int(settings.llm_label_lookback_days)
    result = run_coro(_label_comments_batch(limit_value, days))
    logger.info("label_comments_batch processed=%s", result.get("processed"))
    return result


@celery_app.task(name="tasks.llm.backfill_legacy_labels")  # type: ignore[misc]
def backfill_legacy_labels(limit: int = 2000) -> dict[str, Any]:
    result = run_coro(_backfill_legacy_labels(limit))
    logger.info("backfill_legacy_labels processed=%s", result.get("processed"))
    return result


__all__ = ["label_posts_batch", "label_comments_batch", "backfill_legacy_labels"]
