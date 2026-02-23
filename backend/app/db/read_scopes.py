from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_COMMENTS_CORE_LAB_RELATION: str | None = None


async def get_comments_core_lab_relation(session: AsyncSession) -> str:
    """Return the best available relation for “正常业务口径” comments.

    Prefer the DB view `comments_core_lab_v` (core+lab) when present.
    Fallback to the base table `comments` for compatibility during rollout.
    """
    global _COMMENTS_CORE_LAB_RELATION
    if _COMMENTS_CORE_LAB_RELATION is not None:
        return _COMMENTS_CORE_LAB_RELATION

    rel = (
        await session.execute(text("SELECT to_regclass('public.comments_core_lab_v')"))
    ).scalar_one_or_none()
    _COMMENTS_CORE_LAB_RELATION = "comments_core_lab_v" if rel else "comments"
    return _COMMENTS_CORE_LAB_RELATION


__all__ = ["get_comments_core_lab_relation"]

