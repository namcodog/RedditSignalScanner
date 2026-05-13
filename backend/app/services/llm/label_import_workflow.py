from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from sqlalchemy import text as sqltext

from app.db.session import SessionFactory
from app.services.llm.label_contract import (
    normalize_comment_analysis,
    normalize_post_analysis,
    score_comment_analysis,
    score_post_analysis,
)
from app.services.llm.label_persistence import (
    build_comment_label_row,
    build_post_label_row,
    upsert_comment_label_rows,
    upsert_post_label_rows,
)

ProgressCallback = Callable[[str, int, int], None]


@dataclass(slots=True)
class LabelImportWorkflowInput:
    posts_path: Path | None
    comments_path: Path | None
    batch_size: int
    llm_version: str
    model_name: str
    prompt_version: str


@dataclass(slots=True)
class LabelImportWorkflowResult:
    posts_total: int
    posts_imported: int
    comments_total: int
    comments_imported: int


def iter_label_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def chunk_label_items(
    items: list[dict[str, Any]],
    size: int,
) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def fetch_post_hashes(ids: list[int]) -> dict[int, str | None]:
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


async def import_post_label_rows(
    *,
    items: list[dict[str, Any]],
    llm_version: str,
    model_name: str,
    prompt_version: str,
) -> int:
    ids = [int(item.get("id")) for item in items if item.get("id") is not None]
    hashes = await fetch_post_hashes(ids)
    rows: list[dict[str, Any]] = []
    for item in items:
        post_id = item.get("id")
        if post_id is None:
            continue
        post_id = int(post_id)
        analysis = normalize_post_analysis(item)
        score = score_post_analysis(analysis)
        rows.append(
            build_post_label_row(
                post_id=post_id,
                text_norm_hash=hashes.get(post_id),
                llm_version=llm_version,
                model_name=model_name,
                prompt_version=prompt_version,
                analysis=analysis,
                score={
                    "value_score": score.value_score,
                    "opportunity_score": score.opportunity_score,
                    "business_pool": score.business_pool,
                },
                input_chars=0,
                output_chars=0,
            )
        )
    if not rows:
        return 0
    async with SessionFactory() as session:
        await upsert_post_label_rows(session=session, rows=rows)
        await session.commit()
    return len(rows)


async def import_comment_label_rows(
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
        analysis = normalize_comment_analysis(item)
        score = score_comment_analysis(analysis)
        rows.append(
            build_comment_label_row(
                comment_id=comment_id,
                llm_version=llm_version,
                model_name=model_name,
                prompt_version=prompt_version,
                analysis=analysis,
                score={
                    "value_score": score.value_score,
                    "opportunity_score": score.opportunity_score,
                    "business_pool": score.business_pool,
                },
                input_chars=0,
                output_chars=0,
            )
        )
    if not rows:
        return 0
    async with SessionFactory() as session:
        await upsert_comment_label_rows(session=session, rows=rows)
        await session.commit()
    return len(rows)


async def import_label_files(
    *,
    workflow_input: LabelImportWorkflowInput,
    progress_callback: ProgressCallback | None = None,
) -> LabelImportWorkflowResult:
    posts_total = 0
    posts_imported = 0
    comments_total = 0
    comments_imported = 0

    if workflow_input.posts_path and workflow_input.posts_path.exists():
        posts = list(iter_label_jsonl(workflow_input.posts_path))
        posts_total = len(posts)
        for chunk in chunk_label_items(posts, workflow_input.batch_size):
            posts_imported += await import_post_label_rows(
                items=chunk,
                llm_version=workflow_input.llm_version,
                model_name=workflow_input.model_name,
                prompt_version=workflow_input.prompt_version,
            )
            if progress_callback:
                progress_callback("posts", posts_imported, posts_total)

    if workflow_input.comments_path and workflow_input.comments_path.exists():
        comments = list(iter_label_jsonl(workflow_input.comments_path))
        comments_total = len(comments)
        for chunk in chunk_label_items(comments, workflow_input.batch_size):
            comments_imported += await import_comment_label_rows(
                items=chunk,
                llm_version=workflow_input.llm_version,
                model_name=workflow_input.model_name,
                prompt_version=workflow_input.prompt_version,
            )
            if progress_callback:
                progress_callback("comments", comments_imported, comments_total)

    return LabelImportWorkflowResult(
        posts_total=posts_total,
        posts_imported=posts_imported,
        comments_total=comments_total,
        comments_imported=comments_imported,
    )


__all__ = [
    "LabelImportWorkflowInput",
    "LabelImportWorkflowResult",
    "chunk_label_items",
    "fetch_post_hashes",
    "import_comment_label_rows",
    "import_label_files",
    "import_post_label_rows",
    "iter_label_jsonl",
]
