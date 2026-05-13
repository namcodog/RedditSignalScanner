from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.services.llm.label_persistence import (
    build_comment_label_row,
    build_post_label_row,
    upsert_comment_label_rows,
    upsert_post_label_rows,
)
from app.services.semantic.llm_term_sync import sync_llm_terms


@dataclass(slots=True, frozen=True)
class LabelResultPersistenceDeps:
    upsert_post_label_rows: Callable[..., Awaitable[int]]
    upsert_comment_label_rows: Callable[..., Awaitable[int]]
    sync_llm_terms: Callable[..., Awaitable[Any]]


def build_default_label_result_persistence_deps() -> LabelResultPersistenceDeps:
    return LabelResultPersistenceDeps(
        upsert_post_label_rows=upsert_post_label_rows,
        upsert_comment_label_rows=upsert_comment_label_rows,
        sync_llm_terms=sync_llm_terms,
    )


async def persist_incremental_post_analysis(
    *,
    session: Any,
    row_by_id: dict[int, dict[str, Any]],
    labeler: Any,
    prompt_version: str,
    item_id: int,
    analysis: dict[str, Any],
    score: dict[str, Any],
    input_chars: int,
    output_chars: int,
    deps: LabelResultPersistenceDeps | None = None,
) -> None:
    effective_deps = deps or build_default_label_result_persistence_deps()
    row = row_by_id.get(int(item_id))
    if not row:
        raise KeyError(f"post row not found for item_id={item_id}")

    label_row = build_post_label_row(
        post_id=int(item_id),
        text_norm_hash=row.get("text_norm_hash"),
        llm_version=prompt_version,
        model_name=labeler.model_name,
        prompt_version=labeler.prompt_version,
        analysis=analysis,
        score=score,
        input_chars=input_chars,
        output_chars=output_chars,
    )
    await effective_deps.upsert_post_label_rows(session=session, rows=[label_row])
    await effective_deps.sync_llm_terms(
        session,
        analysis=analysis,
        llm_version=prompt_version,
        prompt_version=labeler.prompt_version,
    )


async def persist_incremental_comment_analysis(
    *,
    session: Any,
    labeler: Any,
    prompt_version: str,
    item_id: int,
    analysis: dict[str, Any],
    score: dict[str, Any],
    input_chars: int,
    output_chars: int,
    deps: LabelResultPersistenceDeps | None = None,
) -> None:
    effective_deps = deps or build_default_label_result_persistence_deps()

    label_row = build_comment_label_row(
        comment_id=int(item_id),
        llm_version=prompt_version,
        model_name=labeler.model_name,
        prompt_version=labeler.prompt_version,
        analysis=analysis,
        score=score,
        input_chars=input_chars,
        output_chars=output_chars,
    )
    await effective_deps.upsert_comment_label_rows(session=session, rows=[label_row])
    await effective_deps.sync_llm_terms(
        session,
        analysis=analysis,
        llm_version=prompt_version,
        prompt_version=labeler.prompt_version,
    )


__all__ = [
    "LabelResultPersistenceDeps",
    "build_default_label_result_persistence_deps",
    "persist_incremental_comment_analysis",
    "persist_incremental_post_analysis",
]
