from __future__ import annotations

import uuid
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discovered_community import DiscoveredCommunity
from app.models.community_pool import CommunityPool
from app.core.celery_app import celery_app
from app.services.discovery.auto_backfill_service import plan_auto_backfill_posts_targets
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.utils.subreddit import subreddit_key

BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_candidate_vetting_backfill(
    *,
    session: AsyncSession,
    community: str,
    trigger: str,
    days: int = 30,
    slice_days: int = 7,
    total_posts_budget: int = 300,
) -> list[str]:
    """
    第4：candidate 先验毒回填，再评估。

    口径：
    - 只对 discovered_communities.status='pending' 的社区生效
    - 幂等：如果 metrics.vetting 已存在且处于 queued/running/completed，就不重复下单
    - 回填用固定配额：meta.budget_cap=True（避免“补到爽”）
    """
    name = subreddit_key(community)
    now = _utc_now()

    row = await session.execute(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == name)
    )
    dc = row.scalars().first()
    if dc is None:
        return []
    if str(dc.status or "") != "pending":
        return []

    # Hard gate: if the community is blacklisted in the pool, do not schedule vetting backfill.
    pool_row = await session.execute(
        select(CommunityPool.is_blacklisted).where(CommunityPool.name == name)
    )
    if pool_row.scalar_one_or_none() is True:
        return []

    metrics: dict[str, Any] = dict(dc.metrics or {})
    vetting: dict[str, Any] = dict(metrics.get("vetting") or {})
    status = str(vetting.get("status") or "")
    if status in {"queued", "running", "completed"}:
        return []

    crawl_run_id = str(uuid.uuid4())
    vetting.update(
        {
            "status": "queued",
            "trigger": str(trigger or ""),
            "days": int(days),
            "slice_days": int(slice_days),
            "total_posts_budget": int(total_posts_budget),
            "crawl_run_id": crawl_run_id,
            "started_at": now.isoformat(),
        }
    )
    metrics["vetting"] = vetting

    dc.metrics = metrics
    dc.updated_at = now
    await session.flush()

    target_ids = await plan_auto_backfill_posts_targets(
        session=session,
        crawl_run_id=crawl_run_id,
        communities=[name],
        now=now,
        days=int(days),
        slice_days=int(slice_days),
        total_posts_budget=int(total_posts_budget),
        reason="candidate_vetting",
    )

    if target_ids:
        for target_id in target_ids:
            await enqueue_execute_target_outbox(
                session,
                target_id=target_id,
                queue=BACKFILL_POSTS_QUEUE,
            )

    return target_ids


async def check_vetting_and_trigger_evaluation(
    *, session: AsyncSession, community: str
) -> bool:
    """当验毒回填完成时，best-effort 触发单社区评估。"""
    name = subreddit_key(community)
    row = await session.execute(
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == name)
    )
    dc = row.scalars().first()
    if dc is None:
        return False

    metrics: dict[str, Any] = dict(dc.metrics or {})
    vetting: dict[str, Any] = dict(metrics.get("vetting") or {})
    crawl_run_id = str(vetting.get("crawl_run_id") or "").strip()
    if not crawl_run_id:
        return False

    stats = await session.execute(
        text(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN status IN ('completed','partial') THEN 1 ELSE 0 END) AS done
            FROM crawler_run_targets
            WHERE crawl_run_id = CAST(:rid AS uuid)
              AND subreddit = :sub
            """
        ),
        {"rid": crawl_run_id, "sub": name},
    )
    total, done = stats.one()
    total = int(total or 0)
    done = int(done or 0)
    if total <= 0 or done < total:
        return False

    now = _utc_now()
    vetting["status"] = "completed"
    vetting["completed_at"] = now.isoformat()
    metrics["vetting"] = vetting
    dc.metrics = metrics
    dc.updated_at = now
    await session.flush()

    try:
        celery_app.send_task(
            "tasks.discovery.evaluate_community",
            kwargs={"community": name},
            queue="probe_queue",
        )
    except Exception:
        # best-effort only
        return True

    return True


__all__ = ["ensure_candidate_vetting_backfill", "check_vetting_and_trigger_evaluation"]
