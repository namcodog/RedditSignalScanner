from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.crawl.planner_workflow import (
    BackfillBootstrapPlannerInput,
    LowQualityPlannerInput,
    PlannerWorkflowDeps,
    SeedSamplingPlannerInput,
    plan_backfill_bootstrap_workflow,
    plan_low_quality_communities_workflow,
    plan_seed_sampling_workflow,
)
from app.services.crawl.target_planner import QueuePlannedTargetsDeps
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox


async def _commit_session(session: Any, *, context: str) -> bool:
    del context
    await session.commit()
    return True


def _planner_workflow_deps() -> PlannerWorkflowDeps:
    return PlannerWorkflowDeps(
        session_factory=SessionFactory,
        ensure_crawler_run=ensure_crawler_run,
        commit_session=_commit_session,
        queue_deps=QueuePlannedTargetsDeps(
            session_factory=SessionFactory,
            enqueue_target_outbox=enqueue_execute_target_outbox,
            commit_session=_commit_session,
        ),
        log_swallowed_exception=lambda *_: None,
    )


async def _reset_tables() -> None:
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await session.execute(text("DELETE FROM community_cache"))
        await session.commit()


@pytest.mark.asyncio
async def test_plan_backfill_bootstrap_workflow_enqueues_targets() -> None:
    await _reset_tables()

    now = datetime.now(timezone.utc)
    community_needs = f"r/backfill_needs_{uuid.uuid4().hex[:8]}"
    community_done = f"r/backfill_done_{uuid.uuid4().hex[:8]}"

    async with SessionFactory() as session:
        session.add_all(
            [
                CommunityPool(
                    name=community_needs,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
                CommunityPool(
                    name=community_done,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
            ]
        )
        session.add_all(
            [
                CommunityCache(
                    community_name=community_needs,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="NEEDS",
                    backfill_cursor="t3_cursor",
                ),
                CommunityCache(
                    community_name=community_done,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="DONE_12M",
                ),
            ]
        )
        await session.commit()

    result = await plan_backfill_bootstrap_workflow(
        BackfillBootstrapPlannerInput(
            now=now,
            max_targets=50000,
            posts_limit=123,
            window_days=365,
            cooldown_minutes=0,
            error_cooldown_minutes=360,
        ),
        deps=_planner_workflow_deps(),
    )

    assert result.status == "planned"
    assert result.inserted >= 1
    assert result.enqueued >= 1
    assert result.run_id is not None

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                  AND subreddit = :subreddit
                """
            ),
            {"rid": result.run_id, "subreddit": community_needs},
        )
        cfg = row.scalar_one()
        outbox = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM task_outbox
                WHERE event_type = 'execute_target'
                  AND payload->>'queue' = 'backfill_queue'
                """
            )
        )
        outbox_count = int(outbox.scalar() or 0)

    plan = cfg if isinstance(cfg, dict) else {}
    assert plan.get("plan_kind") == "backfill_posts"
    assert plan.get("limits", {}).get("posts_limit") == 123
    assert plan.get("meta", {}).get("cursor_after") == "t3_cursor"
    assert outbox_count >= 1


@pytest.mark.asyncio
async def test_plan_seed_sampling_workflow_enqueues_capped_only() -> None:
    await _reset_tables()

    now = datetime.now(timezone.utc)
    needs_seed = f"r/seed_needed_{uuid.uuid4().hex[:8]}"
    recent_seed = f"r/seed_recent_{uuid.uuid4().hex[:8]}"

    async with SessionFactory() as session:
        session.add_all(
            [
                CommunityPool(
                    name=needs_seed,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
                CommunityPool(
                    name=recent_seed,
                    tier="high",
                    categories={},
                    description_keywords={},
                    is_active=True,
                    is_blacklisted=False,
                ),
            ]
        )
        session.add_all(
            [
                CommunityCache(
                    community_name=needs_seed,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="NEEDS",
                    backfill_capped=True,
                    sample_posts=200,
                ),
                CommunityCache(
                    community_name=recent_seed,
                    last_crawled_at=now,
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.50"),
                    backfill_status="NEEDS",
                    backfill_capped=True,
                    sample_posts=200,
                ),
            ]
        )
        await session.commit()

    recent_run_id = str(uuid.uuid4())
    recent_target_id = str(uuid.uuid4())
    async with SessionFactory() as session:
        await ensure_crawler_run(session, crawl_run_id=recent_run_id)
        await ensure_crawler_run_target(
            session,
            community_run_id=recent_target_id,
            crawl_run_id=recent_run_id,
            subreddit=recent_seed,
            status="completed",
            plan_kind="seed_top_year",
            idempotency_key="seed_recent",
            idempotency_key_human="seed_recent",
            config={"plan_kind": "seed_top_year"},
        )
        await session.commit()

    result = await plan_seed_sampling_workflow(
        SeedSamplingPlannerInput(
            now=now,
            cooldown_days=30,
            max_targets=10,
            posts_limit=200,
            min_posts=200,
        ),
        deps=_planner_workflow_deps(),
    )

    assert result.status == "planned"
    assert result.inserted >= 2
    assert result.enqueued >= 2
    assert result.run_id is not None

    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                  AND subreddit = :subreddit
                """
            ),
            {"rid": result.run_id, "subreddit": needs_seed},
        )
        inserted_count = int(rows.scalar() or 0)
        outbox = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM task_outbox
                WHERE event_type = 'execute_target'
                  AND payload->>'queue' = 'backfill_queue'
                """
            )
        )
        outbox_count = int(outbox.scalar() or 0)

    assert inserted_count == 2
    assert outbox_count >= 2


@pytest.mark.asyncio
async def test_plan_low_quality_communities_workflow_enqueues_stale_low_quality_only() -> None:
    await _reset_tables()

    now = datetime.now(timezone.utc)
    target_name = f"r/low_quality_{uuid.uuid4().hex[:8]}"
    fresh_name = f"r/fresh_quality_{uuid.uuid4().hex[:8]}"
    strong_name = f"r/strong_quality_{uuid.uuid4().hex[:8]}"

    async with SessionFactory() as session:
        session.add_all(
            [
                CommunityCache(
                    community_name=target_name,
                    last_crawled_at=now - timedelta(hours=12),
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.20"),
                    avg_valid_posts=10,
                    is_active=True,
                ),
                CommunityCache(
                    community_name=fresh_name,
                    last_crawled_at=now - timedelta(hours=1),
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.20"),
                    avg_valid_posts=10,
                    is_active=True,
                ),
                CommunityCache(
                    community_name=strong_name,
                    last_crawled_at=now - timedelta(hours=12),
                    posts_cached=0,
                    ttl_seconds=3600,
                    quality_score=Decimal("0.80"),
                    avg_valid_posts=80,
                    is_active=True,
                ),
            ]
        )
        await session.commit()

    result = await plan_low_quality_communities_workflow(
        LowQualityPlannerInput(
            now=now,
            stale_hours=8,
            max_targets=50,
            posts_limit=100,
            time_filter="month",
            sort="top",
            hot_cache_ttl_hours=48,
        ),
        deps=_planner_workflow_deps(),
    )

    assert result.status == "planned"
    assert result.total == 1
    assert result.inserted == 1
    assert result.enqueued == 1
    assert result.run_id is not None

    async with SessionFactory() as session:
        row = await session.execute(
            text(
                """
                SELECT subreddit, config
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                """
            ),
            {"rid": result.run_id},
        )
        record = row.mappings().one()
        outbox = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM task_outbox
                WHERE payload->>'queue' = 'patrol_queue'
                """
            )
        )
        outbox_count = int(outbox.scalar() or 0)

    assert record["subreddit"] == target_name
    config = record["config"] if isinstance(record["config"], dict) else {}
    assert config.get("plan_kind") == "patrol"
    assert config.get("reason") == "low_quality_refresh"
    assert outbox_count >= 1
