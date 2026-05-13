from __future__ import annotations

import logging
from typing import Any, Sequence

from app.services.llm.label_contract import (
    LLMScoreResult,
    normalize_comment_analysis,
    normalize_post_analysis,
    score_comment_analysis,
    score_post_analysis,
)
from app.services.llm.labeling_support import (
    build_comment_batch_prompt,
    build_comment_prompt,
    build_post_batch_prompt,
    build_post_prompt,
    extract_batch_items,
    safe_json_loads,
    safe_json_loads_any,
)


async def run_label_post(
    *,
    client: Any,
    title: str,
    body: str,
    subreddit: str,
    comments: Sequence[str],
    max_body_chars: int,
    max_comment_chars: int,
) -> tuple[dict[str, Any], LLMScoreResult, int, int]:
    prompt = build_post_prompt(
        title=title,
        body=body,
        subreddit=subreddit,
        comments=comments,
        max_body_chars=max_body_chars,
        max_comment_chars=max_comment_chars,
    )
    raw = await client.generate(
        prompt,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=512,
    )
    parsed = safe_json_loads(raw)
    analysis = normalize_post_analysis(parsed)
    score = score_post_analysis(analysis)
    input_chars = sum(len(message.get("content") or "") for message in prompt)
    output_chars = len(raw or "")
    return analysis, score, input_chars, output_chars


async def run_label_posts_batch(
    *,
    client: Any,
    items: Sequence[dict[str, Any]],
    max_body_chars: int,
    max_comment_chars: int,
    model_name: str,
    prompt_version: str,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    if not items:
        return []
    prompt = build_post_batch_prompt(
        items=items,
        max_body_chars=max_body_chars,
        max_comment_chars=max_comment_chars,
    )
    raw = await client.generate(
        prompt,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1024,
    )
    parsed = safe_json_loads_any(raw)
    batch_items = extract_batch_items(parsed)
    if not batch_items:
        logger.warning(
            "LLMLabeler.label_posts_batch empty_or_unparseable_response model=%s prompt_version=%s batch_size=%s",
            model_name,
            prompt_version,
            len(items),
        )
        return []

    input_chars = sum(len(message.get("content") or "") for message in prompt)
    output_chars = len(raw or "")
    divisor = max(1, len(batch_items))
    per_input = max(1, input_chars // divisor)
    per_output = max(1, output_chars // divisor)

    results: list[dict[str, Any]] = []
    for item in batch_items:
        item_id = item.get("id")
        if item_id is None:
            continue
        analysis = normalize_post_analysis(item)
        score = score_post_analysis(analysis)
        results.append(
            {
                "id": int(item_id),
                "analysis": analysis,
                "score": score,
                "input_chars": per_input,
                "output_chars": per_output,
            }
        )
    return results


async def run_label_comment(
    *,
    client: Any,
    body: str,
    post_title: str,
    subreddit: str,
    max_body_chars: int,
) -> tuple[dict[str, Any], LLMScoreResult, int, int]:
    prompt = build_comment_prompt(
        body=body,
        post_title=post_title,
        subreddit=subreddit,
        max_body_chars=max_body_chars,
    )
    raw = await client.generate(
        prompt,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=512,
    )
    parsed = safe_json_loads(raw)
    analysis = normalize_comment_analysis(parsed)
    score = score_comment_analysis(analysis)
    input_chars = sum(len(message.get("content") or "") for message in prompt)
    output_chars = len(raw or "")
    return analysis, score, input_chars, output_chars


async def run_label_comments_batch(
    *,
    client: Any,
    items: Sequence[dict[str, Any]],
    max_body_chars: int,
    model_name: str,
    prompt_version: str,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    if not items:
        return []
    prompt = build_comment_batch_prompt(
        items=items,
        max_body_chars=max_body_chars,
    )
    raw = await client.generate(
        prompt,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1024,
    )
    parsed = safe_json_loads_any(raw)
    batch_items = extract_batch_items(parsed)
    if not batch_items:
        logger.warning(
            "LLMLabeler.label_comments_batch empty_or_unparseable_response model=%s prompt_version=%s batch_size=%s",
            model_name,
            prompt_version,
            len(items),
        )
        return []

    input_chars = sum(len(message.get("content") or "") for message in prompt)
    output_chars = len(raw or "")
    divisor = max(1, len(batch_items))
    per_input = max(1, input_chars // divisor)
    per_output = max(1, output_chars // divisor)

    results: list[dict[str, Any]] = []
    for item in batch_items:
        item_id = item.get("id")
        if item_id is None:
            continue
        analysis = normalize_comment_analysis(item)
        score = score_comment_analysis(analysis)
        results.append(
            {
                "id": int(item_id),
                "analysis": analysis,
                "score": score,
                "input_chars": per_input,
                "output_chars": per_output,
            }
        )
    return results


__all__ = [
    "run_label_comment",
    "run_label_comments_batch",
    "run_label_post",
    "run_label_posts_batch",
]
