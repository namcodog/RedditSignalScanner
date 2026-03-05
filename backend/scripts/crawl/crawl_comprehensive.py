#!/usr/bin/env python3
"""
回填抓取组合器（收口版）

说明：
- 只负责“生成 plan + enqueue”，不直接写 posts_raw/comments。
- 目前只做 backfill_posts（按时间窗切片），评论回填请用 comments_task 的 Celery 任务。
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from celery.result import AsyncResult

# Ensure `import app.*` works when invoked from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawl.time_slicer import TimeSlice, generate_slices
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.utils.asyncio_runner import run as run_coro
from app.utils.subreddit import subreddit_key

BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _plan_backfill_posts_and_persist(
    *,
    crawl_run_id: str,
    subreddit: str,
    slices: list[TimeSlice],
    posts_limit: int,
    reason: str,
) -> list[tuple[str, str, str]]:
    targets: list[tuple[str, str, str]] = []
    async with SessionFactory() as session:
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={"mode": "backfill_posts", "reason": reason},
        )
        for ts in slices:
            plan = CrawlPlanContract(
                plan_kind="backfill_posts",
                target_type="subreddit",
                target_value=subreddit,
                reason=reason,
                window=CrawlPlanWindow(since=ts.start, until=ts.end),
                limits=CrawlPlanLimits(posts_limit=max(1, int(posts_limit))),
                meta={"sort": "new"},
            )
            idempotency_key = compute_idempotency_key(plan)
            idempotency_key_human = compute_idempotency_key_human(plan)
            target_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
                )
            )
            await ensure_crawler_run_target(
                session,
                community_run_id=target_id,
                crawl_run_id=crawl_run_id,
                subreddit=subreddit,
                status="queued",
                plan_kind=plan.plan_kind,
                idempotency_key=idempotency_key,
                idempotency_key_human=idempotency_key_human,
                config=plan.model_dump(mode="json"),
            )
            targets.append((target_id, idempotency_key, idempotency_key_human))
        await session.commit()
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description="回填抓取组合器（生成 plan + enqueue）")
    parser.add_argument("--communities", nargs="+", required=True, help="社区列表，如 r/a r/b")
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--since", type=str, default=None, help="ISO8601 (可选)")
    parser.add_argument("--until", type=str, default=None, help="ISO8601 (可选)")
    parser.add_argument("--slice-days", type=int, default=7)
    parser.add_argument("--posts-limit", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    since_dt = _parse_dt(args.since) if args.since else now - timedelta(days=int(args.lookback_days))
    until_dt = _parse_dt(args.until) if args.until else now

    slices = generate_slices(
        since_dt,
        until_dt,
        slice_days=max(1, int(args.slice_days)),
        overlap_seconds=0,
    )
    if not slices:
        raise SystemExit("没有可执行的时间窗（since >= until）")

    crawl_run_id = str(uuid.uuid4())
    communities = [subreddit_key(c) for c in args.communities]
    print(
        f"[INFO] crawl_run_id={crawl_run_id} communities={len(communities)} slices={len(slices)}"
    )

    if args.dry_run:
        for c in communities:
            for ts in slices:
                print(f"[DRY] {c} {ts.start.isoformat()}..{ts.end.isoformat()}")
        return

    results: List[AsyncResult] = []
    for c in communities:
        targets = run_coro(
            _plan_backfill_posts_and_persist(
                crawl_run_id=crawl_run_id,
                subreddit=c,
                slices=slices,
                posts_limit=int(args.posts_limit),
                reason="cold_start",
            )
        )
        for target_id, idempotency_key, human in targets:
            res: AsyncResult = celery_app.send_task(
                "tasks.crawler.execute_target",
                kwargs={"target_id": target_id},
                queue=BACKFILL_POSTS_QUEUE,
            )
            print(
                f"[ENQUEUE] {res.id} target_id={target_id} key={idempotency_key} {human}"
            )
            results.append(res)

    if args.wait:
        for res in results:
            print("[RESULT]", res.get(timeout=None))


if __name__ == "__main__":
    main()
