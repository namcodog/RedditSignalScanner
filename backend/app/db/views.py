"""Read-only views for latest scores with a single rule_version.

This centralises the source of truth for scoring reads to avoid mixing
legacy columns on posts_raw/comments. Downstream services should import
these helpers instead of joining *_scores directly.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any


async def fetch_latest_post_scores(session: AsyncSession) -> list[dict[str, Any]]:
    """Return latest post scores via view (prefer non-rulebook_v1 if present)."""
    result = await session.execute(text("SELECT * FROM post_scores_latest_v"))
    return [dict(row._mapping) for row in result]


async def fetch_latest_comment_scores(session: AsyncSession) -> list[dict[str, Any]]:
    """Return latest comment scores via view (prefer non-rulebook_v1 if present)."""
    result = await session.execute(text("SELECT * FROM comment_scores_latest_v"))
    return [dict(row._mapping) for row in result]
