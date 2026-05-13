from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.services.community.community_pool_loader import CommunityProfile


@dataclass(slots=True)
class PatrolPlannerWorkflowInput:
    force_refresh: bool = False


@dataclass(slots=True)
class PatrolPlannerWorkflowDeps:
    load_seed_profiles: Callable[[bool], Awaitable[tuple[list[CommunityProfile], int]]]
    maybe_trigger_probe_hot_fallback: Callable[..., Awaitable[bool]]
    ensure_parent_run: Callable[[str, bool], Awaitable[None]]
    rank_profiles: Callable[[list[CommunityProfile]], Awaitable[list[CommunityProfile]]]
    plan_patrol_targets: Callable[[str, list[CommunityProfile], bool], Awaitable[dict[str, Any]]]
    generate_run_id: Callable[[], str]
    log_warning: Callable[[str], None]


@dataclass(slots=True)
class PatrolPlannerWorkflowResult:
    status: str
    mode: str = "patrol_planner"
    run_id: str | None = None
    total: int = 0
    due: int = 0
    inserted: int = 0
    enqueued: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": self.mode,
            "run_id": self.run_id,
            "total": self.total,
            "due": self.due,
            "inserted": self.inserted,
            "enqueued": self.enqueued,
        }


async def run_patrol_planner_workflow(
    workflow_input: PatrolPlannerWorkflowInput,
    *,
    deps: PatrolPlannerWorkflowDeps,
) -> PatrolPlannerWorkflowResult:
    seeds, total_pool_count = await deps.load_seed_profiles(workflow_input.force_refresh)

    seed_profiles = [
        profile
        for profile in seeds
        if profile.tier.lower() in ("high", "medium", "low", "gold", "silver", "seed")
    ]
    if not seed_profiles:
        if workflow_input.force_refresh:
            deps.log_warning("⚠️ 强制刷新后仍未找到符合条件的社区")
        else:
            await deps.maybe_trigger_probe_hot_fallback(
                due_count=0,
                total_pool_count=total_pool_count,
            )
        return PatrolPlannerWorkflowResult(
            status="idle",
            total=total_pool_count,
            due=0,
            inserted=0,
            enqueued=0,
        )

    crawl_run_id = deps.generate_run_id()

    if not workflow_input.force_refresh:
        await deps.maybe_trigger_probe_hot_fallback(
            due_count=len(seed_profiles),
            total_pool_count=total_pool_count,
        )

    await deps.ensure_parent_run(crawl_run_id, workflow_input.force_refresh)
    ranked_profiles = await deps.rank_profiles(seed_profiles)
    plan_stats = await deps.plan_patrol_targets(
        crawl_run_id,
        ranked_profiles,
        workflow_input.force_refresh,
    )
    return PatrolPlannerWorkflowResult(
        status="planned",
        run_id=crawl_run_id,
        total=total_pool_count,
        due=len(ranked_profiles),
        inserted=int(plan_stats.get("inserted", 0)),
        enqueued=int(plan_stats.get("enqueued", 0)),
    )


__all__ = [
    "PatrolPlannerWorkflowDeps",
    "PatrolPlannerWorkflowInput",
    "PatrolPlannerWorkflowResult",
    "run_patrol_planner_workflow",
]
