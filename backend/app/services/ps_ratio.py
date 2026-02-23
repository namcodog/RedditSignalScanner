from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.read_scopes import get_comments_core_lab_relation


async def compute_ps_ratio_from_labels(
    session: AsyncSession,
    *,
    since_days: int = 30,
    subreddits: Optional[Iterable[str]] = None,
) -> Optional[float]:
    """Compute Problem/Solution ratio from content_labels on comments.

    Returns a float ratio (pain / max(1, solution)) or None if no data.
    """
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    subs_list = [s.lower().lstrip("r/") for s in (subreddits or []) if s]

    comments_rel = await get_comments_core_lab_relation(session)
    sql = f"""
    WITH target_comments AS (
        SELECT c.id
        FROM {comments_rel} c
        WHERE c.created_utc >= :since
        AND (:has_subs = FALSE OR lower(c.subreddit) = ANY(:subs))
    ), counts AS (
        SELECT
            SUM(CASE WHEN cl.category = 'pain' THEN 1 ELSE 0 END) AS pain_cnt,
            SUM(CASE WHEN cl.category = 'solution' THEN 1 ELSE 0 END) AS sol_cnt
        FROM content_labels cl
        JOIN target_comments tc ON tc.id = cl.content_id
        WHERE cl.content_type = 'comment'
    )
    SELECT pain_cnt, sol_cnt FROM counts
    """
    params = {
        "since": since_dt,
        "has_subs": bool(subs_list),
        "subs": subs_list if subs_list else [""],
    }
    res = await session.execute(text(sql), params)
    row = res.first()
    if not row:
        return None
    pain = int(row[0] or 0)
    sol = int(row[1] or 0)
    denom = max(1, sol)
    if pain == 0 and sol == 0:
        return None
    return float(pain) / float(denom)
