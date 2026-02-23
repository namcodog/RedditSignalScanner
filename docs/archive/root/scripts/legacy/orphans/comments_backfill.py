#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from typing import List

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.reddit_client import RedditAPIClient
from app.services.comments_ingest import persist_comments
from app.services.labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)


async def _run(subreddit: str, ids: List[str], limit: int) -> None:
    settings = get_settings()
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
            for pid in ids:
                items = await reddit.fetch_post_comments(
                    pid, sort="confidence", depth=8, limit=limit, mode="full"
                )
                if not items:
                    continue
                await persist_comments(
                    session,
                    source_post_id=pid,
                    subreddit=subreddit.replace("r/", ""),
                    comments=items,
                )
                comment_ids = [c.get("id") for c in items if c.get("id")]
                await classify_and_label_comments(session, comment_ids)
                await extract_and_label_entities_for_comments(session, comment_ids)
            await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill full comment trees and label them")
    parser.add_argument("--subreddit", required=True, help="Subreddit name, e.g., r/homegym")
    parser.add_argument("--ids", required=True, help="Comma-separated post ids like t3_abc,t3_def")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    sub = args.subreddit.strip()
    ids = [x.strip().replace("t3_", "") for x in args.ids.split(",") if x.strip()]
    asyncio.run(_run(sub, ids, max(100, min(2000, int(args.limit)))))


if __name__ == "__main__":
    main()

