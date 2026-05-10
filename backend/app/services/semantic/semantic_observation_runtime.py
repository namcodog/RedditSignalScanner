from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Literal, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import ContentEntity, ContentLabel
from app.models.llm_labels import CommentLLMLabel, PostLLMLabel
from app.services.semantic.semantic_observation_sync import (
    SemanticSyncResult,
    sync_semantic_observations,
)

ContentKind = Literal["post", "comment"]
RowT = TypeVar("RowT")


def _normalize_content_ids(content_ids: Iterable[int]) -> list[int]:
    unique_ids: set[int] = set()
    ordered: list[int] = []
    for raw in content_ids:
        value = int(raw)
        if value in unique_ids:
            continue
        unique_ids.add(value)
        ordered.append(value)
    return ordered


def _group_rows_by_content_id(rows: Iterable[RowT]) -> dict[int, list[RowT]]:
    grouped: dict[int, list[RowT]] = defaultdict(list)
    for row in rows:
        grouped[int(row.content_id)].append(row)
    return dict(grouped)


async def _load_content_labels(
    session: AsyncSession,
    *,
    content_type: ContentKind,
    content_ids: list[int],
) -> dict[int, list[ContentLabel]]:
    rows = (
        await session.execute(
            select(ContentLabel).where(
                ContentLabel.content_type == content_type,
                ContentLabel.content_id.in_(content_ids),
            )
        )
    ).scalars().all()
    return _group_rows_by_content_id(rows)


async def _load_content_entities(
    session: AsyncSession,
    *,
    content_type: ContentKind,
    content_ids: list[int],
) -> dict[int, list[ContentEntity]]:
    rows = (
        await session.execute(
            select(ContentEntity).where(
                ContentEntity.content_type == content_type,
                ContentEntity.content_id.in_(content_ids),
            )
        )
    ).scalars().all()
    return _group_rows_by_content_id(rows)


async def _load_post_llm_labels(
    session: AsyncSession,
    *,
    post_ids: list[int],
) -> dict[int, PostLLMLabel]:
    rows = (
        await session.execute(
            select(PostLLMLabel).where(PostLLMLabel.post_id.in_(post_ids))
        )
    ).scalars().all()
    return {int(row.post_id): row for row in rows}


async def _load_comment_llm_labels(
    session: AsyncSession,
    *,
    comment_ids: list[int],
) -> dict[int, CommentLLMLabel]:
    rows = (
        await session.execute(
            select(CommentLLMLabel).where(CommentLLMLabel.comment_id.in_(comment_ids))
        )
    ).scalars().all()
    return {int(row.comment_id): row for row in rows}


async def refresh_semantic_observations_for_contents(
    session: AsyncSession,
    *,
    content_type: ContentKind,
    content_ids: Iterable[int],
) -> list[SemanticSyncResult]:
    normalized_ids = _normalize_content_ids(content_ids)
    if not normalized_ids:
        return []
    if content_type not in {"post", "comment"}:
        raise ValueError(f"unsupported content_type={content_type}")

    labels_by_id = await _load_content_labels(
        session,
        content_type=content_type,
        content_ids=normalized_ids,
    )
    entities_by_id = await _load_content_entities(
        session,
        content_type=content_type,
        content_ids=normalized_ids,
    )
    post_labels = (
        await _load_post_llm_labels(session, post_ids=normalized_ids)
        if content_type == "post"
        else {}
    )
    comment_labels = (
        await _load_comment_llm_labels(session, comment_ids=normalized_ids)
        if content_type == "comment"
        else {}
    )

    results: list[SemanticSyncResult] = []
    for content_id in normalized_ids:
        results.append(
            await sync_semantic_observations(
                session,
                content_type=content_type,
                content_id=content_id,
                post_llm_label=post_labels.get(content_id),
                comment_llm_label=comment_labels.get(content_id),
                content_labels=labels_by_id.get(content_id, ()),
                content_entities=entities_by_id.get(content_id, ()),
            )
        )
    return results


__all__ = ["refresh_semantic_observations_for_contents"]
