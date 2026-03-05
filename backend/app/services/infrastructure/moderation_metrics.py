from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.read_scopes import get_comments_core_lab_relation


async def compute_removal_ratio_by_subreddit(
    session: AsyncSession,
    *,
    since_days: int = 30,
    subreddits: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    """Compute removal ratio per subreddit based on comments.removed_by_category.

    Returns mapping subreddit -> removal_ratio in [0,1].
    """
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    subs_list = [s.replace("r/", "").lower() for s in (subreddits or []) if s]
    comments_rel = await get_comments_core_lab_relation(session)
    res = await session.execute(
        text(
            f"""
            SELECT lower(subreddit) AS sub,
                   COUNT(*)::float AS total,
                   SUM(CASE WHEN removed_by_category IS NOT NULL AND removed_by_category <> '' THEN 1 ELSE 0 END)::float AS removed
            FROM {comments_rel}
            WHERE created_utc >= :since
              AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
            GROUP BY lower(subreddit)
            """
        ),
        {"since": since_dt, "has_subs": bool(subs_list), "subs": subs_list or [""]},
    )
    ratios: Dict[str, float] = {}
    for sub, total, removed in res.fetchall():
        total_f = float(total or 0.0)
        if total_f <= 0.0:
            ratios[str(sub)] = 0.0
            continue
        ratios[str(sub)] = max(0.0, min(1.0, float(removed or 0.0) / total_f))
    return ratios


def to_rules_friendliness_score(removal_ratio: float) -> int:
    """Convert removal ratio to friendliness score (0-100).

    Simple mapping: score = round(100 * (1 - removal_ratio)).
    """
    r = max(0.0, min(1.0, float(removal_ratio)))
    return int(round(100.0 * (1.0 - r)))
