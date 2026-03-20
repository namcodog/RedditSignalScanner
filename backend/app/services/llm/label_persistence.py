from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from sqlalchemy import text as sqltext

_POST_LABEL_UPSERT_SQL = sqltext(
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
)

_COMMENT_LABEL_UPSERT_SQL = sqltext(
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
)


def _score_value(score: Mapping[str, Any], key: str) -> Any:
    return score.get(key)


def _entities_json(analysis: Mapping[str, Any]) -> str:
    return json.dumps(analysis.get("entities") or {})


def build_post_label_row(
    *,
    post_id: int,
    text_norm_hash: str | None,
    llm_version: str,
    model_name: str,
    prompt_version: str,
    analysis: Mapping[str, Any],
    score: Mapping[str, Any],
    input_chars: int,
    output_chars: int,
) -> dict[str, Any]:
    return {
        "post_id": int(post_id),
        "text_norm_hash": text_norm_hash,
        "llm_version": llm_version,
        "model_name": model_name,
        "prompt_version": prompt_version,
        "value_score": _score_value(score, "value_score"),
        "opportunity_score": _score_value(score, "opportunity_score"),
        "business_pool": _score_value(score, "business_pool"),
        "sentiment": analysis.get("sentiment"),
        "purchase_intent_score": analysis.get("purchase_intent_score"),
        "tags_analysis": json.dumps(dict(analysis)),
        "entities_extracted": _entities_json(analysis),
        "input_chars": int(input_chars),
        "output_chars": int(output_chars),
    }


def build_comment_label_row(
    *,
    comment_id: int,
    llm_version: str,
    model_name: str,
    prompt_version: str,
    analysis: Mapping[str, Any],
    score: Mapping[str, Any],
    input_chars: int,
    output_chars: int,
) -> dict[str, Any]:
    return {
        "comment_id": int(comment_id),
        "llm_version": llm_version,
        "model_name": model_name,
        "prompt_version": prompt_version,
        "value_score": _score_value(score, "value_score"),
        "opportunity_score": _score_value(score, "opportunity_score"),
        "business_pool": _score_value(score, "business_pool"),
        "sentiment": analysis.get("sentiment"),
        "purchase_intent_score": analysis.get("purchase_intent_score"),
        "tags_analysis": json.dumps(dict(analysis)),
        "entities_extracted": _entities_json(analysis),
        "input_chars": int(input_chars),
        "output_chars": int(output_chars),
    }


async def upsert_post_label_rows(
    *,
    session: Any,
    rows: Sequence[Mapping[str, Any]],
) -> int:
    if not rows:
        return 0
    await session.execute(_POST_LABEL_UPSERT_SQL, list(rows))
    return len(rows)


async def upsert_comment_label_rows(
    *,
    session: Any,
    rows: Sequence[Mapping[str, Any]],
) -> int:
    if not rows:
        return 0
    await session.execute(_COMMENT_LABEL_UPSERT_SQL, list(rows))
    return len(rows)


__all__ = [
    "build_comment_label_row",
    "build_post_label_row",
    "upsert_comment_label_rows",
    "upsert_post_label_rows",
]
