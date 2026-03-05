from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text as sqltext

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.llm.labeling import (
    _normalize_comment_analysis,
    _normalize_post_analysis,
    _score_comment,
    _score_post,
)
from app.utils.asyncio_runner import run as run_coro


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _chunk(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _fetch_post_hashes(ids: list[int]) -> dict[int, str | None]:
    if not ids:
        return {}
    async with SessionFactory() as session:
        result = await session.execute(
            sqltext(
                """
                SELECT id, text_norm_hash
                FROM posts_raw
                WHERE id = ANY(:ids)
                """
            ),
            {"ids": ids},
        )
        return {int(row.id): row.text_norm_hash for row in result.all()}


async def _upsert_posts(
    *,
    items: list[dict[str, Any]],
    llm_version: str,
    model_name: str,
    prompt_version: str,
) -> int:
    ids = [int(item.get("id")) for item in items if item.get("id") is not None]
    hashes = await _fetch_post_hashes(ids)
    rows: list[dict[str, Any]] = []
    for item in items:
        post_id = item.get("id")
        if post_id is None:
            continue
        post_id = int(post_id)
        analysis = _normalize_post_analysis(item)
        score = _score_post(analysis)
        rows.append(
            {
                "post_id": post_id,
                "text_norm_hash": hashes.get(post_id),
                "llm_version": llm_version,
                "model_name": model_name,
                "prompt_version": prompt_version,
                "value_score": score.value_score,
                "opportunity_score": score.opportunity_score,
                "business_pool": score.business_pool,
                "sentiment": analysis.get("sentiment"),
                "purchase_intent_score": analysis.get("purchase_intent_score"),
                "tags_analysis": json.dumps(analysis),
                "entities_extracted": json.dumps(analysis.get("entities") or {}),
                "input_chars": 0,
                "output_chars": 0,
            }
        )
    if not rows:
        return 0
    async with SessionFactory() as session:
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
            rows,
        )
        await session.commit()
    return len(rows)


async def _upsert_comments(
    *,
    items: list[dict[str, Any]],
    llm_version: str,
    model_name: str,
    prompt_version: str,
) -> int:
    rows: list[dict[str, Any]] = []
    for item in items:
        comment_id = item.get("id")
        if comment_id is None:
            continue
        comment_id = int(comment_id)
        analysis = _normalize_comment_analysis(item)
        score = _score_comment(analysis)
        rows.append(
            {
                "comment_id": comment_id,
                "llm_version": llm_version,
                "model_name": model_name,
                "prompt_version": prompt_version,
                "value_score": score.value_score,
                "opportunity_score": score.opportunity_score,
                "business_pool": score.business_pool,
                "sentiment": analysis.get("sentiment"),
                "purchase_intent_score": analysis.get("purchase_intent_score"),
                "tags_analysis": json.dumps(analysis),
                "entities_extracted": json.dumps(analysis.get("entities") or {}),
                "input_chars": 0,
                "output_chars": 0,
            }
        )
    if not rows:
        return 0
    async with SessionFactory() as session:
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
            rows,
        )
        await session.commit()
    return len(rows)


async def _import_labels(
    *,
    posts_path: Path | None,
    comments_path: Path | None,
    batch_size: int,
    llm_version: str,
    model_name: str,
    prompt_version: str,
) -> None:
    if posts_path and posts_path.exists():
        posts = list(_iter_jsonl(posts_path))
        total = 0
        for chunk in _chunk(posts, batch_size):
            total += await _upsert_posts(
                items=chunk,
                llm_version=llm_version,
                model_name=model_name,
                prompt_version=prompt_version,
            )
            print(f"[posts] imported {total}/{len(posts)}")
    if comments_path and comments_path.exists():
        comments = list(_iter_jsonl(comments_path))
        total = 0
        for chunk in _chunk(comments, batch_size):
            total += await _upsert_comments(
                items=chunk,
                llm_version=llm_version,
                model_name=model_name,
                prompt_version=prompt_version,
            )
            print(f"[comments] imported {total}/{len(comments)}")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--posts", type=Path, default=None)
    parser.add_argument("--comments", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--llm-version", default=settings.llm_label_prompt_version)
    parser.add_argument("--model-name", default=settings.llm_label_model_name)
    parser.add_argument("--prompt-version", default=settings.llm_label_prompt_version)
    args = parser.parse_args()

    run_coro(
        _import_labels(
            posts_path=args.posts,
            comments_path=args.comments,
            batch_size=max(1, int(args.batch_size)),
            llm_version=str(args.llm_version),
            model_name=str(args.model_name),
            prompt_version=str(args.prompt_version),
        )
    )


if __name__ == "__main__":
    main()
