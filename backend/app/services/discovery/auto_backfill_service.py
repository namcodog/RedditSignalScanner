from __future__ import annotations

import uuid
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.community_pool import CommunityPool
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawl.time_slicer import generate_slices
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.utils.subreddit import subreddit_key

BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")


def _allocate_posts_budget_per_slice(*, total_posts_budget: int, slices_count: int) -> list[int]:
    total = max(0, int(total_posts_budget))
    count = max(0, int(slices_count))
    if total <= 0 or count <= 0:
        return []
    base = total // count
    remainder = total % count
    return [base + (1 if i < remainder else 0) for i in range(count)]


async def plan_auto_backfill_posts_targets(
    *,
    session: AsyncSession,
    crawl_run_id: str,
    communities: list[str],
    now: datetime,
    days: int = 30,
    slice_days: int = 7,
    total_posts_budget: int = 300,
    max_targets: int | None = None,
    reason: str = "auto_backfill_after_approval",
) -> list[str]:
    """
    P1 最小闭环：评估通过后，自动给社区下单“30天回填 posts” targets（固定配额上限）。

    口径：
    - 每个社区按时间窗切片（默认 7 天一片）
    - 每个社区总 posts 预算 = total_posts_budget（默认 300），均分到各 slice
    - meta.budget_cap=True：表示这是“额度回填”，不追求把窗口扫干净
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Safety: never auto-backfill communities that are already blacklisted in community_pool.
    # (Prevents "pollution" and avoids burning budget on explicitly blocked subs.)
    normalized = [subreddit_key(raw) for raw in communities if str(raw or "").strip()]
    if not normalized:
        return []

    try:
        rows = await session.execute(
            select(CommunityPool.name).where(
                CommunityPool.name.in_(sorted(set(normalized))),
                CommunityPool.is_blacklisted.is_(True),
            )
        )
        blacklisted = {str(r[0]) for r in rows.all() if r and r[0]}
    except Exception:
        blacklisted = set()

    communities = [c for c in normalized if c not in blacklisted]
    if not communities:
        return []

    lookback_days = max(1, int(days))
    since_dt = now - timedelta(days=lookback_days)
    until_dt = now

    slices = generate_slices(
        since_dt,
        until_dt,
        slice_days=max(1, int(slice_days)),
        overlap_seconds=0,
    )
    if not slices:
        return []

    budgets = _allocate_posts_budget_per_slice(
        total_posts_budget=int(total_posts_budget),
        slices_count=len(slices),
    )
    if not budgets:
        return []

    # best-effort: ensure parent run exists (FK safety)
    await ensure_crawler_run(
        session,
        crawl_run_id=crawl_run_id,
        config={
            "mode": "auto_backfill_posts",
            "days": lookback_days,
            "slice_days": max(1, int(slice_days)),
            "total_posts_budget": int(total_posts_budget),
            "reason": reason,
        },
    )

    targets: list[str] = []
    cap = None if max_targets is None else max(0, int(max_targets))
    for raw in sorted(set(communities)):
        sub = subreddit_key(raw)
        for ts, posts_limit in zip(slices, budgets, strict=False):
            if cap is not None and len(targets) >= cap:
                return targets
            if int(posts_limit) <= 0:
                continue
            plan = CrawlPlanContract(
                plan_kind="backfill_posts",
                target_type="subreddit",
                target_value=sub,
                reason=reason,
                window=CrawlPlanWindow(since=ts.start, until=ts.end),
                limits=CrawlPlanLimits(posts_limit=max(1, int(posts_limit))),
                meta={
                    "sort": "new",
                    "queue": BACKFILL_POSTS_QUEUE,
                    "budget_cap": True,
                    "auto_backfill_days": lookback_days,
                    "auto_backfill_total_posts_budget": int(total_posts_budget),
                },
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
                subreddit=sub,
                status="queued",
                plan_kind=plan.plan_kind,
                idempotency_key=idempotency_key,
                idempotency_key_human=idempotency_key_human,
                config=plan.model_dump(mode="json"),
            )
            targets.append(target_id)

    return targets


__all__ = ["plan_auto_backfill_posts_targets"]
