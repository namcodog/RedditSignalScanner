from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy import text


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ContentDuplicateLookupInput:
    subreddit: str
    title: str | None
    body: str | None


@dataclass(slots=True)
class ContentDuplicateLookupDeps:
    text_norm_hash_available: Callable[[], Awaitable[bool]]
    execute_query: Callable[[Any, dict[str, Any]], Awaitable[Any]]


async def find_content_duplicate(
    *,
    lookup_input: ContentDuplicateLookupInput,
    deps: ContentDuplicateLookupDeps,
) -> str | None:
    if not await deps.text_norm_hash_available():
        return None

    content = f"{lookup_input.title or ''} {lookup_input.body or ''}".strip()
    if not content:
        return None

    try:
        result = await deps.execute_query(
            text(
                """
                SELECT source_post_id
                FROM posts_raw
                WHERE source = 'reddit'
                  AND subreddit = :subreddit
                  AND text_norm_hash = text_norm_hash(:content)
                ORDER BY fetched_at DESC
                LIMIT 1
                """
            ),
            {"subreddit": lookup_input.subreddit, "content": content},
        )
    except Exception:
        logger.exception("content dedup query failed; skip")
        return None

    row = result.first()
    if row:
        return row[0]
    return None


__all__ = [
    "ContentDuplicateLookupDeps",
    "ContentDuplicateLookupInput",
    "find_content_duplicate",
]
