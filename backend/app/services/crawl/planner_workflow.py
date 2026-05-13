from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import text

from app.services.crawl.target_planner import (
    QueuePlannedTargetsDeps,
    build_backfill_bootstrap_target,
    build_patrol_target,
    build_seed_sampling_targets,
    queue_planned_crawl_targets,
)

@dataclass(slots=True, frozen=True)
class PlannerWorkflowDeps:
    session_factory: Callable[[], Any]
    ensure_crawler_run: Callable[..., Awaitable[Any]]
    commit_session: Callable[..., Awaitable[bool]]
    queue_deps: QueuePlannedTargetsDeps
    log_swallowed_exception: Callable[[str, Exception], None]


@dataclass(slots=True, frozen=True)
class PlannerWorkflowResult:
    status: str
    inserted: int
    enqueued: int
    run_id: str | None = None
    total: int | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "inserted": self.inserted,
            "enqueued": self.enqueued,
        }
        if self.run_id:
            payload["run_id"] = self.run_id
        if self.total is not None:
            payload["total"] = self.total
        return payload


@dataclass(slots=True, frozen=True)
class BackfillBootstrapPlannerInput:
    now: datetime
    max_targets: int
    posts_limit: int
    window_days: int
    cooldown_minutes: int
    error_cooldown_minutes: int
    queue: str = "backfill_queue"


@dataclass(slots=True, frozen=True)
class SeedSamplingPlannerInput:
    now: datetime
    cooldown_days: int
    max_targets: int
    posts_limit: int
    min_posts: int
    queue: str = "backfill_queue"


@dataclass(slots=True, frozen=True)
class LowQualityPlannerInput:
    now: datetime
    stale_hours: int
    max_targets: int
    posts_limit: int
    time_filter: str
    sort: str
    hot_cache_ttl_hours: int


async def _ensure_run_best_effort(
    *,
    crawl_run_id: str,
    config: dict[str, object],
    deps: PlannerWorkflowDeps,
    context: str,
) -> None:
    try:
        async with deps.session_factory() as session:
            await deps.ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config=config,
            )
            await deps.commit_session(session, context=context)
    except Exception as exc:
        deps.log_swallowed_exception(f"{context} ensure_run failed", exc)


async def plan_backfill_bootstrap_workflow(
    params: BackfillBootstrapPlannerInput,
    *,
    deps: PlannerWorkflowDeps,
) -> PlannerWorkflowResult:
    cooldown_dt = params.now - timedelta(minutes=params.cooldown_minutes)
    error_cooldown_dt = params.now - timedelta(minutes=params.error_cooldown_minutes)
    since_dt = params.now - timedelta(days=params.window_days)

    async with deps.session_factory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        rows = await session.execute(
            text(
                """
                SELECT c.community_name, c.backfill_cursor
                FROM community_cache c
                JOIN community_pool p ON p.name = c.community_name
                LEFT JOIN crawler_run_targets t
                  ON t.subreddit = c.community_name
                 AND t.plan_kind = 'backfill_posts'
                 AND t.status IN ('queued', 'running')
                WHERE p.is_active IS TRUE
                  AND p.is_blacklisted IS FALSE
                  AND (
                        c.backfill_status IS NULL
                        OR c.backfill_status IN ('NEEDS', 'ERROR')
                  )
                  AND (
                        c.backfill_status != 'ERROR'
                        OR c.backfill_updated_at IS NULL
                        OR c.backfill_updated_at < :error_cooldown
                  )
                  AND (
                        c.last_attempt_at IS NULL
                        OR c.last_attempt_at < :cooldown
                  )
                  AND t.id IS NULL
                ORDER BY c.last_attempt_at NULLS FIRST
                LIMIT :limit
                """
            ),
            {
                "cooldown": cooldown_dt,
                "error_cooldown": error_cooldown_dt,
                "limit": params.max_targets,
            },
        )
        targets = [(str(row[0]), row[1]) for row in rows.all() if row[0]]

    if not targets:
        return PlannerWorkflowResult(status="idle", inserted=0, enqueued=0)

    crawl_run_id = str(uuid.uuid4())
    await _ensure_run_best_effort(
        crawl_run_id=crawl_run_id,
        config={
            "mode": "backfill_bootstrap_planner",
            "window_days": params.window_days,
            "posts_limit": params.posts_limit,
        },
        deps=deps,
        context="plan_backfill_bootstrap",
    )

    queue_result = await queue_planned_crawl_targets(
        crawl_run_id=crawl_run_id,
        targets=[
            build_backfill_bootstrap_target(
                subreddit=name,
                cursor_after=str(cursor_after) if cursor_after else None,
                since=since_dt,
                until=params.now,
                posts_limit=params.posts_limit,
                window_days=params.window_days,
                queue=params.queue,
            )
            for name, cursor_after in targets
        ],
        deps=deps.queue_deps,
        commit_context="plan_backfill_bootstrap",
    )

    return PlannerWorkflowResult(
        status="planned",
        inserted=queue_result.inserted,
        enqueued=queue_result.enqueued,
        run_id=crawl_run_id,
        total=len(targets),
    )


async def plan_seed_sampling_workflow(
    params: SeedSamplingPlannerInput,
    *,
    deps: PlannerWorkflowDeps,
) -> PlannerWorkflowResult:
    cooldown_dt = params.now - timedelta(days=params.cooldown_days)

    async with deps.session_factory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        rows = await session.execute(
            text(
                """
                WITH last_seed AS (
                    SELECT subreddit, MAX(started_at) AS last_seed_at
                    FROM crawler_run_targets
                    WHERE plan_kind IN ('seed_top_year', 'seed_top_all', 'seed_controversial_year')
                      AND status IN ('completed', 'partial')
                    GROUP BY subreddit
                )
                SELECT c.community_name
                FROM community_cache c
                JOIN community_pool p ON p.name = c.community_name
                LEFT JOIN last_seed s ON s.subreddit = c.community_name
                WHERE p.is_active IS TRUE
                  AND p.is_blacklisted IS FALSE
                  AND c.backfill_capped IS TRUE
                  AND COALESCE(c.sample_posts, 0) >= :min_posts
                  AND (s.last_seed_at IS NULL OR s.last_seed_at < :cooldown)
                ORDER BY s.last_seed_at NULLS FIRST
                LIMIT :limit
                """
            ),
            {
                "cooldown": cooldown_dt,
                "limit": params.max_targets,
                "min_posts": params.min_posts,
            },
        )
        communities = [str(row[0]) for row in rows.all() if row[0]]

    if not communities:
        return PlannerWorkflowResult(status="idle", inserted=0, enqueued=0)

    crawl_run_id = str(uuid.uuid4())
    await _ensure_run_best_effort(
        crawl_run_id=crawl_run_id,
        config={
            "mode": "seed_sampling_planner",
            "cooldown_days": params.cooldown_days,
            "posts_limit": params.posts_limit,
        },
        deps=deps,
        context="plan_seed_sampling",
    )

    targets = []
    for community_name in communities:
        targets.extend(
            build_seed_sampling_targets(
                subreddit=community_name,
                posts_limit=params.posts_limit,
                queue=params.queue,
            )
        )

    queue_result = await queue_planned_crawl_targets(
        crawl_run_id=crawl_run_id,
        targets=targets,
        deps=deps.queue_deps,
        commit_context="plan_seed_sampling",
    )

    return PlannerWorkflowResult(
        status="planned",
        inserted=queue_result.inserted,
        enqueued=queue_result.enqueued,
        run_id=crawl_run_id,
        total=len(communities),
    )


async def plan_low_quality_communities_workflow(
    params: LowQualityPlannerInput,
    *,
    deps: PlannerWorkflowDeps,
) -> PlannerWorkflowResult:
    cutoff_dt = params.now - timedelta(hours=params.stale_hours)

    async with deps.session_factory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        rows = await session.execute(
            text(
                """
                SELECT c.community_name
                FROM community_cache c
                WHERE c.last_crawled_at < :cutoff
                  AND c.avg_valid_posts < 50
                  AND c.is_active IS TRUE
                ORDER BY c.last_crawled_at ASC
                LIMIT :limit
                """
            ),
            {
                "cutoff": cutoff_dt,
                "limit": params.max_targets,
            },
        )
        communities = [str(row[0]) for row in rows.all() if row[0]]

    if not communities:
        return PlannerWorkflowResult(status="idle", inserted=0, enqueued=0)

    crawl_run_id = str(uuid.uuid4())
    await _ensure_run_best_effort(
        crawl_run_id=crawl_run_id,
        config={"mode": "low_quality_patrol_planner"},
        deps=deps,
        context="plan_low_quality_communities",
    )

    queue_result = await queue_planned_crawl_targets(
        crawl_run_id=crawl_run_id,
        targets=[
            build_patrol_target(
                subreddit=community_name,
                reason="low_quality_refresh",
                posts_limit=params.posts_limit,
                time_filter=params.time_filter,
                sort=params.sort,
                hot_cache_ttl_hours=params.hot_cache_ttl_hours,
            )
            for community_name in communities
        ],
        deps=deps.queue_deps,
        commit_context="plan_low_quality_communities",
    )

    return PlannerWorkflowResult(
        status="planned",
        inserted=queue_result.inserted,
        enqueued=queue_result.enqueued,
        run_id=crawl_run_id,
        total=len(communities),
    )


__all__ = [
    "BackfillBootstrapPlannerInput",
    "LowQualityPlannerInput",
    "PlannerWorkflowDeps",
    "PlannerWorkflowResult",
    "SeedSamplingPlannerInput",
    "plan_backfill_bootstrap_workflow",
    "plan_low_quality_communities_workflow",
    "plan_seed_sampling_workflow",
]
