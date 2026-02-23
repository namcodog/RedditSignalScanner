#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.reddit_client import RedditAPIClient
from app.services.subreddit_snapshot import persist_subreddit_snapshot


async def _run(subreddit: str) -> None:
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
        about = await reddit.fetch_subreddit_about(subreddit.replace("r/", ""))
        rules = await reddit.fetch_subreddit_rules(subreddit.replace("r/", ""))
        async with SessionFactory() as session:
            await persist_subreddit_snapshot(
                session,
                subreddit=subreddit.replace("r/", ""),
                subscribers=about.get("subscribers"),
                active_user_count=about.get("active_user_count"),
                rules_text=rules,
                over18=about.get("over18"),
            )
            await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture subreddit snapshot (about + rules)")
    parser.add_argument("--subreddit", required=True, help="Subreddit name, e.g., r/homegym")
    args = parser.parse_args()
    asyncio.run(_run(args.subreddit.strip()))


if __name__ == "__main__":
    main()

