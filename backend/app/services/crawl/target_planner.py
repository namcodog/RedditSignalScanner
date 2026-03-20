from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Sequence

from sqlalchemy import select

from app.models.community_cache import CommunityCache
from app.services.community.community_pool_loader import CommunityProfile
from app.services.crawl.crawler_config import TierSettings
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.utils.subreddit import subreddit_key


@dataclass(slots=True, frozen=True)
class PlannedCrawlTarget:
    subreddit: str
    queue: str
    plan: CrawlPlanContract
    dedupe_key: str | None = None


@dataclass(slots=True, frozen=True)
class PlannedTargetCounts:
    inserted: int
    enqueued: int

    def as_dict(self) -> dict[str, int]:
        return {"inserted": self.inserted, "enqueued": self.enqueued}


@dataclass(slots=True, frozen=True)
class QueuePlannedTargetsDeps:
    session_factory: Callable[[], Any]
    enqueue_target_outbox: Callable[..., Awaitable[bool]]
    commit_session: Callable[..., Awaitable[bool]]


@dataclass(slots=True, frozen=True)
class PatrolTargetPlannerDeps:
    session_factory: Callable[[], Any]
    tier_settings_for: Callable[[CommunityProfile | None], TierSettings | None]
    queue_deps: QueuePlannedTargetsDeps
    patrol_default_posts_limit: int
    patrol_max_posts_limit: int
    effective_batch_size: int
    effective_time_filter: str
    effective_sort: str
    effective_hot_cache_ttl_hours: int


def build_patrol_target(
    *,
    subreddit: str,
    reason: str,
    posts_limit: int,
    time_filter: str,
    sort: str,
    hot_cache_ttl_hours: int,
    extra_meta: dict[str, Any] | None = None,
    queue: str = "patrol_queue",
) -> PlannedCrawlTarget:
    normalized_subreddit = subreddit_key(subreddit)
    meta = dict(extra_meta or {})
    meta.setdefault("time_filter", time_filter)
    meta.setdefault("sort", sort)
    meta.setdefault("hot_cache_ttl_hours", hot_cache_ttl_hours)
    meta.setdefault("queue", queue)
    return PlannedCrawlTarget(
        subreddit=normalized_subreddit,
        queue=queue,
        plan=CrawlPlanContract(
            plan_kind="patrol",
            target_type="subreddit",
            target_value=normalized_subreddit,
            reason=reason,
            limits=CrawlPlanLimits(posts_limit=posts_limit),
            meta=meta,
        ),
    )


def build_backfill_bootstrap_target(
    *,
    subreddit: str,
    cursor_after: str | None,
    since: datetime,
    until: datetime,
    posts_limit: int,
    window_days: int,
    queue: str,
) -> PlannedCrawlTarget:
    normalized_subreddit = subreddit_key(subreddit)
    meta: dict[str, Any] = {"sort": "new", "queue": queue}
    if cursor_after:
        meta["cursor_after"] = str(cursor_after)
    return PlannedCrawlTarget(
        subreddit=normalized_subreddit,
        queue=queue,
        dedupe_key=f"backfill_bootstrap:{normalized_subreddit}:{window_days}:{posts_limit}",
        plan=CrawlPlanContract(
            plan_kind="backfill_posts",
            target_type="subreddit",
            target_value=normalized_subreddit,
            reason="bootstrap_backfill",
            window=CrawlPlanWindow(since=since, until=until),
            limits=CrawlPlanLimits(posts_limit=posts_limit),
            meta=meta,
        ),
    )


def build_seed_sampling_targets(
    *,
    subreddit: str,
    posts_limit: int,
    queue: str,
) -> tuple[PlannedCrawlTarget, PlannedCrawlTarget]:
    normalized_subreddit = subreddit_key(subreddit)

    def _build(plan_kind: str) -> PlannedCrawlTarget:
        return PlannedCrawlTarget(
            subreddit=normalized_subreddit,
            queue=queue,
            dedupe_key=f"{plan_kind}:{normalized_subreddit}:{posts_limit}",
            plan=CrawlPlanContract(
                plan_kind=plan_kind,
                target_type="subreddit",
                target_value=normalized_subreddit,
                reason="seed_sampling",
                limits=CrawlPlanLimits(posts_limit=posts_limit),
                meta={"queue": queue},
            ),
        )

    return _build("seed_top_year"), _build("seed_top_all")


def _target_id_for_plan(*, crawl_run_id: str, plan: CrawlPlanContract) -> tuple[str, str, str]:
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    target_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"crawler_run_target:{crawl_run_id}:{idempotency_key}",
        )
    )
    return target_id, idempotency_key, idempotency_key_human


async def queue_planned_crawl_targets(
    *,
    crawl_run_id: str,
    targets: Sequence[PlannedCrawlTarget],
    deps: QueuePlannedTargetsDeps,
    commit_context: str,
) -> PlannedTargetCounts:
    inserted = 0
    enqueued = 0

    if not targets:
        return PlannedTargetCounts(inserted=0, enqueued=0)

    async with deps.session_factory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})

        for target in targets:
            target_id, idempotency_key, idempotency_key_human = _target_id_for_plan(
                crawl_run_id=crawl_run_id,
                plan=target.plan,
            )
            was_inserted = await ensure_crawler_run_target(
                session,
                community_run_id=target_id,
                crawl_run_id=crawl_run_id,
                subreddit=target.subreddit,
                status="queued",
                plan_kind=target.plan.plan_kind,
                idempotency_key=idempotency_key,
                idempotency_key_human=idempotency_key_human,
                dedupe_key=target.dedupe_key,
                config=target.plan.model_dump(mode="json"),
            )
            if not was_inserted:
                continue

            inserted += 1
            if await deps.enqueue_target_outbox(
                session=session,
                target_id=target_id,
                queue=target.queue,
            ):
                enqueued += 1

        await deps.commit_session(session, context=commit_context)

    return PlannedTargetCounts(inserted=inserted, enqueued=enqueued)


async def plan_patrol_targets(
    *,
    crawl_run_id: str,
    profiles: Sequence[CommunityProfile],
    force_refresh: bool,
    deps: PatrolTargetPlannerDeps,
) -> PlannedTargetCounts:
    if not profiles:
        return PlannedTargetCounts(inserted=0, enqueued=0)

    patrol_allowed_time_filters = {"hour", "day"}
    max_targets_per_heartbeat = max(1, int(deps.effective_batch_size or 1))
    sub_keys = [subreddit_key(profile.name) for profile in profiles]

    async with deps.session_factory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        waterline_rows = await session.execute(
            select(
                CommunityCache.community_name,
                CommunityCache.last_seen_post_id,
                CommunityCache.last_seen_created_at,
            ).where(CommunityCache.community_name.in_(sub_keys))
        )
        waterlines = {
            str(row[0]): (row[1], row[2]) for row in waterline_rows.all() if row[0]
        }

    planned_targets: list[PlannedCrawlTarget] = []

    for profile in profiles:
        if len(planned_targets) >= max_targets_per_heartbeat:
            break

        tier_norm = str(profile.tier or "").strip().lower()
        prio_norm = str(profile.priority or "").strip().lower()
        if tier_norm in {"candidate", "blocked"} or prio_norm in {
            "candidate",
            "blocked",
        }:
            continue

        tier_cfg = deps.tier_settings_for(profile)
        raw_post_limit = int(
            getattr(tier_cfg, "post_limit", 0)
            if tier_cfg is not None
            else deps.patrol_default_posts_limit
        )
        if raw_post_limit <= 0:
            raw_post_limit = deps.patrol_default_posts_limit
        post_limit = max(1, min(deps.patrol_max_posts_limit, raw_post_limit))

        raw_time_filter = str(
            getattr(tier_cfg, "time_filter", "")
            if tier_cfg is not None
            else deps.effective_time_filter
        ).strip().lower()
        time_filter = (
            raw_time_filter if raw_time_filter in patrol_allowed_time_filters else "day"
        )
        sort_value = (
            str(tier_cfg.pick_sort(default_sort=deps.effective_sort))
            if tier_cfg is not None
            else deps.effective_sort
        )
        hot_cache_ttl_hours = int(
            tier_cfg.hot_cache_ttl_hours
            if tier_cfg is not None
            else deps.effective_hot_cache_ttl_hours
        )

        sub_key = subreddit_key(profile.name)
        meta: dict[str, Any] = {
            "tier": str(profile.tier),
            "patrol_comments_enabled": False,
        }
        last_seen_post_id, last_seen_created_at = waterlines.get(sub_key, (None, None))
        if last_seen_post_id:
            meta["cursor_last_seen_post_id"] = str(last_seen_post_id)
        if last_seen_created_at is not None:
            meta["cursor_last_seen_created_at"] = (
                last_seen_created_at.astimezone(timezone.utc).isoformat()
                if getattr(last_seen_created_at, "tzinfo", None) is not None
                else str(last_seen_created_at)
            )

        planned_targets.append(
            build_patrol_target(
                subreddit=sub_key,
                reason="cache_expired" if not force_refresh else "manual_force_refresh",
                posts_limit=post_limit,
                time_filter=time_filter,
                sort=sort_value,
                hot_cache_ttl_hours=hot_cache_ttl_hours,
                extra_meta=meta,
            )
        )

    return await queue_planned_crawl_targets(
        crawl_run_id=crawl_run_id,
        targets=planned_targets,
        deps=deps.queue_deps,
        commit_context="plan_patrol_targets",
    )


__all__ = [
    "PatrolTargetPlannerDeps",
    "PlannedCrawlTarget",
    "PlannedTargetCounts",
    "QueuePlannedTargetsDeps",
    "build_backfill_bootstrap_target",
    "build_patrol_target",
    "build_seed_sampling_targets",
    "plan_patrol_targets",
    "queue_planned_crawl_targets",
]
