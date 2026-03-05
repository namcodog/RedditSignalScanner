"""Phase 6: Self-Growing Ecosystem - Weekly Discovery Task

Orchestrates the automated community discovery and evaluation pipeline:
1. Fetch pain keywords from semantic_rules
2. Search Reddit for posts matching those keywords
3. Record new communities as 'pending' candidates
4. Evaluate each pending community using value density scoring
5. Approve high-value communities → CommunityPool
6. Reject low-value communities → Cooldown/Blacklist

Controlled by CRON_DISCOVERY_ENABLED flag (默认开启，可设为 0 关闭).
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.models.discovered_community import DiscoveredCommunity
from app.services.community_discovery import CommunityDiscoveryService
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.discovery.auto_backfill_service import plan_auto_backfill_posts_targets
from app.services.discovery.candidate_vetting_service import (
    check_vetting_and_trigger_evaluation,
    ensure_candidate_vetting_backfill,
)
from app.services.discovery.evaluator_service import CommunityEvaluator
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")


async def _run_semantic_discovery() -> Dict[str, Any]:
    """Execute semantic-driven community discovery.
    
    Phase 6: The Hunter's Eye - Discovers new communities using pain keywords
    from the semantic_rules table.
    """
    settings = get_settings()
    
    async with SessionFactory() as db:
        async with RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
        ) as reddit:
            service = CommunityDiscoveryService(db, reddit)
            
            # Use semantic pain keywords for discovery
            discovered = await service.discover_from_pain_keywords(
                keywords=None,  # Auto-fetch from DB
                max_keywords=20,
                posts_per_keyword=25,
            )
    
    return discovered


async def _run_community_evaluation() -> list[dict[str, Any]]:
    """Evaluate all pending communities.
    
    Phase 6: The Gatekeeper - Evaluates discovered communities and decides
    whether to approve them into CommunityPool or reject with cooldown.
    """
    settings = get_settings()
    
    async with SessionFactory() as db:
        async with RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
        ) as reddit:
            # 第4：先确保 pending 社区都有“验毒回填”在跑（幂等）
            if os.getenv("DISCOVERY_CANDIDATE_VETTING_ENABLED", "1") == "1":
                now = datetime.now(timezone.utc)
                days = int(os.getenv("DISCOVERY_VETTING_DAYS", "30"))
                slice_days = int(os.getenv("DISCOVERY_VETTING_SLICE_DAYS", "7"))
                total_posts_budget = int(os.getenv("DISCOVERY_VETTING_TOTAL_POSTS_BUDGET", "300"))

                pending_rows = await db.execute(
                    select(DiscoveredCommunity.name).where(DiscoveredCommunity.status == "pending")
                )
                pending_names = [str(r[0] or "") for r in pending_rows.all() if str(r[0] or "")]
                for name in pending_names:
                    await ensure_candidate_vetting_backfill(
                        session=db,
                        community=name,
                        trigger="discovery_task",
                        days=days,
                        slice_days=slice_days,
                        total_posts_budget=total_posts_budget,
                    )
                await db.commit()

            evaluator = CommunityEvaluator(db, reddit, sample_size=50)
            results = await evaluator.evaluate_all_pending()

            # P1 最小闭环：approved -> 自动回填 30 天（固定配额上限）
            if os.getenv("DISCOVERY_AUTO_BACKFILL_ENABLED", "1") == "1":
                approved = [
                    str(r.get("community") or "").strip()
                    for r in results
                    if str(r.get("status") or "") == "approved"
                ]
                approved = [c for c in approved if c]
                # Safety: never auto-backfill communities that are already blacklisted in the pool.
                if approved:
                    try:
                        from app.models.community_pool import CommunityPool

                        rows = await db.execute(
                            select(CommunityPool.name).where(
                                CommunityPool.name.in_(approved),
                                CommunityPool.is_blacklisted.is_(True),
                            )
                        )
                        blacklisted = {str(r[0]) for r in rows.all() if r and r[0]}
                        if blacklisted:
                            approved = [c for c in approved if c not in blacklisted]
                    except Exception:
                        pass
                if approved:
                    days = int(os.getenv("DISCOVERY_AUTO_BACKFILL_DAYS", "30"))
                    slice_days = int(os.getenv("DISCOVERY_AUTO_BACKFILL_SLICE_DAYS", "7"))
                    total_posts_budget = int(
                        os.getenv("DISCOVERY_AUTO_BACKFILL_TOTAL_POSTS_BUDGET", "300")
                    )
                    reason = "auto_backfill_after_approval"

                    crawl_run_id = str(uuid.uuid4())
                    await ensure_crawler_run(
                        db,
                        crawl_run_id=crawl_run_id,
                        config={
                            "mode": "auto_backfill_after_approval",
                            "source": "discovery_task",
                            "approved_count": len(approved),
                            "approved_sample": approved[:20],
                            "days": days,
                            "slice_days": slice_days,
                            "total_posts_budget": total_posts_budget,
                        },
                    )

                    target_ids = await plan_auto_backfill_posts_targets(
                        session=db,
                        crawl_run_id=crawl_run_id,
                        communities=approved,
                        now=datetime.now(timezone.utc),
                        days=days,
                        slice_days=slice_days,
                        total_posts_budget=total_posts_budget,
                        reason=reason,
                    )
                    for target_id in target_ids:
                        await enqueue_execute_target_outbox(
                            db,
                            target_id=target_id,
                            queue=BACKFILL_POSTS_QUEUE,
                        )
                    await db.commit()
    
    return results


async def _evaluate_single_community(*, community: str) -> dict[str, Any]:
    """单社区评估（验毒回填完成后触发）。"""
    settings = get_settings()
    async with SessionFactory() as db:
        async with RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
        ) as reddit:
            evaluator = CommunityEvaluator(db, reddit, sample_size=50)
            result = await evaluator.evaluate(community)
            await db.commit()
            return dict(result)


async def _check_candidate_vetting(*, community: str) -> dict[str, Any]:
    """验毒回填完成聚合检查（best-effort）。"""
    async with SessionFactory() as db:
        did = await check_vetting_and_trigger_evaluation(session=db, community=community)
        await db.commit()
    return {"status": "completed" if did else "skipped", "community": community}


async def _run_weekly_discovery() -> Dict[str, Any]:
    """Full discovery + evaluation pipeline.
    
    This is the main orchestration function that runs weekly.
    """
    # Gate via env flag
    if os.getenv("CRON_DISCOVERY_ENABLED", "1") != "1":
        return {
            "status": "skipped",
            "reason": "CRON_DISCOVERY_ENABLED!=1",
            "discovered": 0,
            "evaluated": 0,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    
    logger.info("🔍 Phase 6: Starting weekly discovery pipeline...")
    
    # Step 1: Discover new communities
    try:
        discovered = await _run_semantic_discovery()
        logger.info(f"   → Discovered {len(discovered)} new candidates")
    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")
        discovered = []
    
    # Step 2: Evaluate pending communities
    try:
        eval_results = await _run_community_evaluation()
        approved = sum(1 for r in eval_results if r.get("status") == "approved")
        rejected = sum(1 for r in eval_results if r.get("status") in ("rejected", "blacklisted"))
        logger.info(f"   → Evaluated {len(eval_results)}: ✅{approved} | ❌{rejected}")
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        eval_results = []
        approved = rejected = 0
    
    summary = {
        "status": "completed",
        "discovered": len(discovered),
        "discovered_communities": sorted(discovered)[:20],  # Limit for logging
        "evaluated": len(eval_results),
        "approved": approved,
        "rejected": rejected,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    
    logger.info(f"✅ Weekly discovery complete: {summary}")
    return summary


@celery_app.task(name="tasks.discovery.discover_new_communities_weekly")
def discover_new_communities_weekly() -> Dict[str, Any]:
    """Celery entrypoint for weekly community discovery (Phase 6).
    
    Runs every Monday at 4:00 AM (configured in Celery Beat).
    默认开启；如需关闭设 CRON_DISCOVERY_ENABLED=0。
    """
    return asyncio.run(_run_weekly_discovery())


@celery_app.task(name="tasks.discovery.run_semantic_discovery")
def run_semantic_discovery() -> Dict[str, Any]:
    """Manual trigger for semantic discovery only (without evaluation)."""
    if os.getenv("CRON_DISCOVERY_ENABLED", "1") != "1":
        return {"status": "skipped", "reason": "CRON_DISCOVERY_ENABLED!=1"}
    
    discovered = asyncio.run(_run_semantic_discovery())
    return {"status": "completed", "discovered": len(discovered), "communities": sorted(discovered)}


@celery_app.task(name="tasks.discovery.run_community_evaluation")
def run_community_evaluation() -> Dict[str, Any]:
    """Manual trigger for evaluating all pending communities."""
    results = asyncio.run(_run_community_evaluation())
    return {
        "status": "completed",
        "evaluated": len(results),
        "approved": sum(1 for r in results if r.get("status") == "approved"),
        "rejected": sum(1 for r in results if r.get("status") in ("rejected", "blacklisted")),
    }


@celery_app.task(name="tasks.discovery.evaluate_community")
def evaluate_community(*, community: str) -> dict[str, Any]:
    """单社区评估入口（由验毒回填完成后自动触发）。"""
    return asyncio.run(_evaluate_single_community(community=community))


@celery_app.task(name="tasks.discovery.check_candidate_vetting")
def check_candidate_vetting(*, community: str) -> dict[str, Any]:
    """验毒回填完成检查入口（由 backfill_posts target 结束后触发）。"""
    return asyncio.run(_check_candidate_vetting(community=community))


__all__ = [
    "discover_new_communities_weekly",
    "run_semantic_discovery", 
    "run_community_evaluation",
]
