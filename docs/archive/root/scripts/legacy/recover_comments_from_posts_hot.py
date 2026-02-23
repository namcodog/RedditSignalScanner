#!/usr/bin/env python3
from __future__ import annotations

"""
Recover comments by re-crawling from posts_hot within a lookback window.

Usage examples:
  python -u backend/scripts/recover_comments_from_posts_hot.py --days 3 --per-sub 50
  python -u backend/scripts/recover_comments_from_posts_hot.py --days 1 --subreddits r/homegym,r/Fitness

Env overrides (optional):
  RECOVERY_LOOKBACK_DAYS, RECOVERY_POST_LIMIT_PER_SUB, RECOVERY_SUBREDDITS
"""

import argparse
import asyncio
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.comments_ingest import persist_comments
from app.services.labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.services.reddit_client import RedditAPIClient


async def _select_posts(days: int, sub_filter: List[str] | None) -> Dict[str, List[str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    per_sub_limit = int(os.getenv("RECOVERY_POST_LIMIT_PER_SUB", "100"))
    subs: Dict[str, List[str]] = defaultdict(list)
    async with SessionFactory() as session:
        where_sub = ""
        params: dict = {"cutoff": cutoff}
        if sub_filter:
            where_sub = " AND lower(subreddit) = ANY(:subs)"
            params["subs"] = [s.lower().replace("r/", "") for s in sub_filter]
        rows = await session.execute(
            text(
                f"""
                SELECT subreddit, source_post_id
                FROM posts_hot
                WHERE created_at >= :cutoff
                {where_sub}
                ORDER BY created_at DESC
                """
            ),
            params,
        )
        for sub, pid in rows.fetchall():
            key = str(sub).lower()
            if len(subs[key]) < per_sub_limit:
                subs[key].append(str(pid))
    return subs


async def _recover(days: int, sub_filter: List[str] | None) -> Tuple[int, int]:
    settings = get_settings()
    subs = await _select_posts(days, sub_filter)
    if not subs:
        return 0, 0
    processed = 0
    labeled = 0
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    ) as reddit:
        async with SessionFactory() as session:
            for sub, posts in subs.items():
                for pid in posts:
                    try:
                        items = await reddit.fetch_post_comments(
                            pid, sort="confidence", depth=8, limit=500, mode="full"
                        )
                        if not items:
                            continue
                        await persist_comments(session, source_post_id=pid, subreddit=sub, comments=items)
                        ids = [c.get("id") for c in items if c.get("id")]
                        labeled += await classify_and_label_comments(session, ids)
                        labeled += await extract_and_label_entities_for_comments(session, ids)
                        processed += len(items)
                    except Exception:
                        continue
            await session.commit()
    return processed, labeled


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover comments by re-crawling posts_hot window")
    parser.add_argument("--days", type=int, default=int(os.getenv("RECOVERY_LOOKBACK_DAYS", "3")))
    parser.add_argument("--per-sub", type=int, default=int(os.getenv("RECOVERY_POST_LIMIT_PER_SUB", "100")))
    parser.add_argument("--subreddits", type=str, default=os.getenv("RECOVERY_SUBREDDITS", ""))
    args = parser.parse_args()

    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    processed, labeled = asyncio.run(_recover(args.days, subs or None))
    print({"status": "ok", "processed": processed, "labeled": labeled})


if __name__ == "__main__":
    main()

