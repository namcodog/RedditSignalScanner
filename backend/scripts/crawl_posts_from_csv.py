#!/usr/bin/env python3
from __future__ import annotations

"""
Fetch posts for subreddits provided via CSV or CLI and ingest into the DB.

Use cases:
  - Next-high-value pool (15 subs) for the last 12 months
  - Run per shard CSV produced by split_subreddit_csv.py

Examples:
  python -u backend/scripts/crawl_posts_from_csv.py --csv ./次高价值社区池_15社区_shard1_of_3.csv --months 12
  python -u backend/scripts/crawl_posts_from_csv.py --subs r/shopify,r/Fitness --since 2024-01 --until 2024-12

The script is non-interactive; it honours the global Redis rate limiter and
performs sliced fetches by month to overcome Reddit listing caps.
"""

import argparse
import asyncio
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.utils.subreddit import normalize_subreddit_name
from app.services.infrastructure.global_rate_limiter import GlobalRateLimiter
import redis.asyncio as redis  # type: ignore


def _read_csv(path: Path) -> List[str]:
    headers: Sequence[str] = []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        rows = list(r)
    name_col = next((c for c in ("社区名称", "subreddit", "name") if c in headers), None)
    if not name_col:
        raise ValueError("CSV must contain a '社区名称' (or 'subreddit'/'name') column")
    subs: List[str] = []
    for row in rows:
        v = (row.get(name_col) or "").strip()
        if not v:
            continue
        subs.append(v)
    return subs


def _build_month_slices_from_months(months: int) -> List[tuple[int, int]]:
    now = datetime.now(timezone.utc)
    # start from the first day of the month (months-1 months ago)
    start_month = (now.month - (months - 1) - 1) % 12 + 1
    start_year = now.year + ((now.month - (months - 1) - 1) // 12)
    cur = datetime(start_year, start_month, 1, tzinfo=timezone.utc)
    slices: List[tuple[int, int]] = []
    for _ in range(months):
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1)
        else:
            nxt = cur.replace(month=cur.month + 1)
        slices.append((int(cur.timestamp()), int((nxt - timedelta(seconds=1)).timestamp())))
        cur = nxt
    return slices


def _build_month_slices_since_until(since: str, until: str) -> List[tuple[int, int]]:
    def to_dt(ym: str) -> datetime:
        return datetime.strptime(ym + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    cur = to_dt(since)
    end = to_dt(until)
    if end.month == 12:
        end_next = end.replace(year=end.year + 1, month=1)
    else:
        end_next = end.replace(month=end.month + 1)
    slices: List[tuple[int, int]] = []
    while cur < end_next:
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1)
        else:
            nxt = cur.replace(month=cur.month + 1)
        slices.append((int(cur.timestamp()), int((nxt - timedelta(seconds=1)).timestamp())))
        cur = nxt
    return slices


def _chunk(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


async def _run(
    subs: Iterable[str], *, slices: List[tuple[int, int]], per_slice_max: int, safe_mode: bool, dedupe: bool, ingest_batch_size: int, max_subs: int | None, debug_startup: bool
) -> dict:
    settings = get_settings()
    # Global limiter for all shards/processes
    limiter = None
    try:
        rclient = redis.Redis.from_url(settings.reddit_cache_redis_url)
        limiter = GlobalRateLimiter(
            rclient,
            limit=max(1, int(settings.reddit_rate_limit)),
            window_seconds=max(1, int(settings.reddit_rate_limit_window_seconds)),
            client_id=settings.reddit_client_id or "default",
        )
    except Exception as e:
        print(f"WARN Global rate limiter init failed (posts-from-csv): {e}")

    processed_subs = 0
    total_posts_fetched = 0
    total_new = 0
    total_updated = 0
    total_dups = 0

    if debug_startup:
        print("[startup] limiter_ready=", bool(limiter))

    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=min(settings.reddit_max_concurrency, 2 if safe_mode else settings.reddit_max_concurrency),
        global_rate_limiter=limiter,
    ) as reddit:
        if debug_startup:
            print("[startup] reddit_client_ready=True")
        async with SessionFactory() as session:
            if debug_startup:
                print("[startup] db_session_ready=True")
            crawler = IncrementalCrawler(session, reddit, hot_cache_ttl_hours=24)
            processed_count = 0
            for name in subs:
                raw = normalize_subreddit_name(name)
                print(f"==> Fetch posts for r/{raw} ...")
                try:
                    # Stream by month slice to keep memory low; optional in-memory de-dup
                    seen: set[str] = set() if dedupe else set()
                    sub_new = sub_upd = sub_dup = sub_total = 0
                    for start_ts, end_ts in slices:
                        batch = await reddit.fetch_subreddit_posts_by_timestamp(
                            subreddit=raw,
                            start_epoch=start_ts,
                            end_epoch=end_ts,
                            sort="new",
                            max_posts=min(per_slice_max, 200 if safe_mode else per_slice_max),
                        )
                        if not batch:
                            continue
                        # local de-dup to reduce DB roundtrips (optional)
                        use_list = batch if not dedupe else [p for p in batch if p.id not in seen]
                        if dedupe:
                            for p in use_list:
                                seen.add(p.id)
                        sub_total += len(use_list)
                        total_posts_fetched += len(use_list)
                        if use_list:
                            # ingest in small batches to keep memory and transaction small
                            for part in _chunk(use_list, max(10, ingest_batch_size)):
                                res = await crawler.ingest_posts_batch(name, part)
                                sub_new += res.get("new", 0)
                                sub_upd += res.get("updated", 0)
                                sub_dup += res.get("duplicates", 0)
                        # free slice memory proactively
                        del batch
                        del use_list
                        import gc as _gc
                        _gc.collect()
                    total_new += sub_new
                    total_updated += sub_upd
                    total_dups += sub_dup
                    processed_subs += 1
                    print(f"   done: new={sub_new} updated={sub_upd} dup={sub_dup} total_posts={sub_total}")
                    processed_count += 1
                    if max_subs and processed_count >= max_subs:
                        break
                except Exception as e:
                    print(f"WARN fetch/ingest failed for r/{raw}: {e}")
                    continue

    return {
        "processed_subs": processed_subs,
        "posts_fetched": total_posts_fetched,
        "new": total_new,
        "updated": total_updated,
        "duplicates": total_dups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch subreddit posts from CSV or list and ingest")
    parser.add_argument("--csv", type=str, default="", help="CSV with 列 '社区名称' (or 'subreddit'/'name')")
    parser.add_argument("--subs", type=str, default="", help="Comma-separated list like r/a,r/b")
    parser.add_argument("--months", type=int, default=12, help="Lookback months (when --since/--until not set)")
    parser.add_argument("--since", type=str, default="", help="YYYY-MM (overrides --months)")
    parser.add_argument("--until", type=str, default="", help="YYYY-MM (overrides --months)")
    parser.add_argument("--per-slice", type=int, default=1000, help="Max posts per month slice")
    parser.add_argument("--safe", action="store_true", help="Low-memory mode: per-slice<=200, concurrency<=2")
    parser.add_argument("--dedupe", action="store_true", help="Enable in-memory de-dup within a subreddit")
    parser.add_argument("--ingest-batch", type=int, default=50, help="DB ingest batch size (default 50)")
    parser.add_argument("--max-subs", type=int, default=0, help="Process at most N subreddits (0=all)")
    parser.add_argument("--debug-startup", action="store_true", help="Print startup stage markers for diagnosis")
    args = parser.parse_args()

    subs: List[str] = []
    if args.csv:
        subs = _read_csv(Path(args.csv))
    elif args.subs:
        subs = [s.strip() for s in args.subs.split(",") if s.strip()]
    else:
        raise SystemExit("Either --csv or --subs is required")

    if args.since and args.until:
        slices = _build_month_slices_since_until(args.since, args.until)
    else:
        slices = _build_month_slices_from_months(max(1, int(args.months)))
    result = asyncio.run(
        _run(
            subs,
            slices=slices,
            per_slice_max=max(100, int(args.per_slice)),
            safe_mode=bool(args.safe),
            dedupe=bool(args.dedupe),
            ingest_batch_size=max(10, int(args.ingest_batch)),
            max_subs=(int(args.max_subs) if int(args.max_subs) > 0 else None),
            debug_startup=bool(args.debug_startup),
        )
    )
    print(result)


if __name__ == "__main__":
    main()
