from __future__ import annotations

from typing import Any, Optional
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def persist_subreddit_snapshot(
    session: AsyncSession,
    *,
    subreddit: str,
    subscribers: Optional[int | str],
    active_user_count: Optional[int | str],
    rules_text: Optional[str],
    over18: Optional[bool],
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO subreddit_snapshots (subreddit, captured_at, subscribers, active_user_count, rules_text, over18, moderation_score)
            VALUES (:subreddit, NOW(), :subs, :active, :rules, :over18, :modscore)
            """
        ),
        {
            "subreddit": subreddit,
            "subs": str(subscribers) if subscribers is not None else None,
            "active": str(active_user_count) if active_user_count is not None else None,
            "rules": (rules_text or "")[:4000] if rules_text else None,
            "over18": bool(over18) if over18 is not None else None,
            "modscore": None,
        },
    )
