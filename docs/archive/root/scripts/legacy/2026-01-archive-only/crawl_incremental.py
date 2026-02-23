#!/usr/bin/env python3
"""
回填抓取下单器（收口版）

这个脚本不再直接抓 Reddit，也不再写 JSONL。
它只做一件事：把“回填时间窗”拆成一张张 plan，然后丢给 Celery Worker 去跑。

示例：
  PYTHONPATH=backend python backend/scripts/crawl_incremental.py \
    --subreddit r/ecommerce \
    --lookback-days 90 \
    --slice-days 7 \
    --posts-limit 1000
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
from app.services.crawl.time_slicer import TimeSlice, generate_slices
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawler_runs_service import ensure_crawler_run
from app.services.crawler_run_targets_service import ensure_crawler_run_target
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
    """
    只做两件事：
    1) 写 crawler_run_targets.config（Crawl Plan 合同）
    2) 返回 target_id 列表，供脚本 enqueue 执行
    """
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
    parser = argparse.ArgumentParser(description="回填抓取下单器（生成 plan + enqueue）")
    parser.add_argument("--subreddit", required=True, help="子版块，如 r/ecommerce 或 ecommerce")
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--since", type=str, default=None, help="ISO8601 (可选)")
    parser.add_argument("--until", type=str, default=None, help="ISO8601 (可选)")
    parser.add_argument("--slice-days", type=int, default=7, help="默认 7 天一片")
    parser.add_argument("--posts-limit", type=int, default=1000, help="每片最多抓取帖子数")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不发任务")
    parser.add_argument("--wait", action="store_true", help="等待所有任务完成（本地调试用）")
    args = parser.parse_args()

    sub_key = subreddit_key(args.subreddit)
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
    print(f"[INFO] crawl_run_id={crawl_run_id} subreddit={sub_key} slices={len(slices)}")

    if args.dry_run:
        for ts in slices:
            print(f"[DRY] {ts.start.isoformat()}..{ts.end.isoformat()}")
        return

    targets = run_coro(
        _plan_backfill_posts_and_persist(
            crawl_run_id=crawl_run_id,
            subreddit=sub_key,
            slices=slices,
            posts_limit=int(args.posts_limit),
            reason="cold_start",
        )
    )

    results: List[AsyncResult] = []
    for target_id, idempotency_key, human in targets:
        res: AsyncResult = celery_app.send_task(
            "tasks.crawler.execute_target",
            kwargs={"target_id": target_id},
            queue=BACKFILL_POSTS_QUEUE,
        )
        print(f"[ENQUEUE] {res.id} target_id={target_id} key={idempotency_key} {human}")
        results.append(res)

    if args.wait:
        for res in results:
            print("[RESULT]", res.get(timeout=None))


if __name__ == "__main__":
    main()
