#!/usr/bin/env python3
"""
Smoke test: crawl a small subset of communities with very conservative rate limits
so we can verify incremental pipeline without triggering Reddit risk control.
"""
import asyncio
from pathlib import Path
import json
import time

import sys
# Ensure backend package is importable when invoked from repo root
backend_path = Path(__file__).resolve().parents[1]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.reddit_client import RedditAPIClient
from app.services.incremental_crawler import IncrementalCrawler
from app.services.community_pool_loader import CommunityPoolLoader


async def main() -> int:
    settings = get_settings()

    # Conservative client config
    reddit = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=min(20, settings.reddit_rate_limit),
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=min(20.0, settings.reddit_request_timeout_seconds),
        max_concurrency=1,
    )

    async with reddit:
        async with SessionFactory() as db:
            loader = CommunityPoolLoader(db)
            seeds = await loader.load_community_pool(force_refresh=False)
            names = [p.name for p in seeds[:5]]  # take first 5 communities only
            crawler = IncrementalCrawler(db=db, reddit_client=reddit, hot_cache_ttl_hours=24)

            results = []
            for name in names:
                r = await crawler.crawl_community_incremental(name, limit=30, time_filter="week")
                print(f"✅ {name}: 新增{r.get('new_posts',0)}, 更新{r.get('updated_posts',0)}, 去重{r.get('duplicates',0)}")
                results.append(r)

    ts = time.strftime("%Y%m%d-%H%M%S")
    out = {
        "status": "completed",
        "communities_run": names,
        "results": results,
    }
    out_path = Path(__file__).resolve().parents[2] / "reports" / "phase-log" / f"T1.1-smoke-{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print("Saved:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

