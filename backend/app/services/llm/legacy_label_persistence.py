from __future__ import annotations

from typing import Any

from app.services.llm.label_persistence import (
    build_comment_label_row,
    build_post_label_row,
    upsert_comment_label_rows,
    upsert_post_label_rows,
)


async def upsert_legacy_post_label(
    *,
    session: Any,
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
    row = build_post_label_row(
        post_id=post_id,
        text_norm_hash=text_norm_hash,
        llm_version=llm_version,
        model_name=model_name,
        prompt_version=prompt_version,
        analysis=analysis,
        score=score,
        input_chars=input_chars,
        output_chars=output_chars,
    )
    await upsert_post_label_rows(session=session, rows=[row])


async def upsert_legacy_comment_label(
    *,
    session: Any,
    comment_id: int,
    llm_version: str,
    model_name: str,
    prompt_version: str,
    analysis: dict[str, Any],
    score: dict[str, Any],
    input_chars: int,
    output_chars: int,
) -> None:
    row = build_comment_label_row(
        comment_id=comment_id,
        llm_version=llm_version,
        model_name=model_name,
        prompt_version=prompt_version,
        analysis=analysis,
        score=score,
        input_chars=input_chars,
        output_chars=output_chars,
    )
    await upsert_comment_label_rows(session=session, rows=[row])


__all__ = [
    "upsert_legacy_comment_label",
    "upsert_legacy_post_label",
]
