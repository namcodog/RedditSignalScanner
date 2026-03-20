from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.services.crawl.plan_contract import CrawlPlanContract


@dataclass(slots=True, frozen=True)
class ExecuteTargetTriggerDeps:
    send_task: Callable[..., Any]
    env_get: Callable[[str, str], str]
    probe_queue: str
    backfill_posts_queue: str


def should_auto_trigger_evaluator(
    *,
    plan: CrawlPlanContract,
    outcome: dict[str, object],
    deps: ExecuteTargetTriggerDeps,
) -> bool:
    if str(plan.plan_kind) != "probe":
        return False
    if deps.env_get("PROBE_AUTO_EVALUATE_ENABLED", "1") != "1":
        return False
    try:
        upserted = int(outcome.get("discovered_communities_upserted") or 0)
    except Exception:
        upserted = 0
    return upserted > 0


def auto_trigger_evaluator_best_effort(
    *,
    plan: CrawlPlanContract,
    outcome: dict[str, object],
    deps: ExecuteTargetTriggerDeps,
) -> None:
    if not should_auto_trigger_evaluator(plan=plan, outcome=outcome, deps=deps):
        return
    try:
        deps.send_task(
            "tasks.discovery.run_community_evaluation",
            queue=deps.probe_queue,
        )
    except Exception:
        return


def maybe_trigger_candidate_vetting_check(
    *,
    plan: CrawlPlanContract,
    deps: ExecuteTargetTriggerDeps,
) -> None:
    if str(plan.plan_kind) != "backfill_posts":
        return
    if str(plan.reason or "") != "candidate_vetting":
        return
    try:
        deps.send_task(
            "tasks.discovery.check_candidate_vetting",
            kwargs={"community": str(plan.target_value)},
            queue=deps.backfill_posts_queue,
        )
    except Exception:
        return


__all__ = [
    "ExecuteTargetTriggerDeps",
    "auto_trigger_evaluator_best_effort",
    "maybe_trigger_candidate_vetting_check",
    "should_auto_trigger_evaluator",
]
