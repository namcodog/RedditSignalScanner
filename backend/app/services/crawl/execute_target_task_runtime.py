from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any

from app.services.crawl.compensation_target_service import CompensationTargetDeps
from app.services.crawl.execute_target_trigger_service import ExecuteTargetTriggerDeps
from app.services.crawl.execute_target_workflow import (
    ExecuteTargetWorkflowDeps,
    ExecuteTargetWorkflowResult,
)

__all__ = [
    "build_execute_target_workflow_deps",
    "run_execute_target_task",
]


@dataclass(frozen=True, slots=True)
class ExecuteTargetTaskRuntimeInput:
    target_id: str


def build_execute_target_workflow_deps(
    *,
    session_factory: Any,
    settings_factory: Any,
    reddit_client_cls: Any,
    execute_crawl_plan_func: Any,
    parse_uuid_func: Any,
    ensure_dict_func: Any,
    audit_missing_target_func: Any,
    rollback_session_quietly_func: Any,
    commit_session_func: Any,
    apply_session_change_func: Any,
    set_target_failed_func: Any,
    set_target_partial_func: Any,
    set_target_completed_func: Any,
    load_community_blacklist_status_func: Any,
    needs_community_lock_func: Any,
    try_acquire_community_lock_func: Any,
    release_community_lock_func: Any,
    build_global_rate_limiter_func: Any,
    finalize_backfill_status_func: Any,
    build_compensation_target_deps_func: Any,
    enqueue_compensation_target_func: Any,
    build_trigger_deps_func: Any,
    auto_trigger_evaluator_best_effort_func: Any,
    maybe_trigger_candidate_vetting_check_func: Any,
    mark_crawl_attempt_func: Any,
    mark_backfill_running_func: Any,
    mark_backfill_status_only_func: Any,
    patrol_target_time_budget_seconds: float,
) -> ExecuteTargetWorkflowDeps:
    compensation_deps: CompensationTargetDeps = build_compensation_target_deps_func()
    trigger_deps: ExecuteTargetTriggerDeps = build_trigger_deps_func()
    return ExecuteTargetWorkflowDeps(
        session_factory=session_factory,
        settings_factory=settings_factory,
        reddit_client_cls=reddit_client_cls,
        execute_crawl_plan=execute_crawl_plan_func,
        parse_uuid=parse_uuid_func,
        ensure_dict=ensure_dict_func,
        audit_missing_target=audit_missing_target_func,
        rollback_session_quietly=rollback_session_quietly_func,
        commit_session=commit_session_func,
        apply_session_change=apply_session_change_func,
        set_target_failed=set_target_failed_func,
        set_target_partial=set_target_partial_func,
        set_target_completed=set_target_completed_func,
        load_community_blacklist_status=load_community_blacklist_status_func,
        needs_community_lock=needs_community_lock_func,
        try_acquire_community_lock=try_acquire_community_lock_func,
        release_community_lock=release_community_lock_func,
        build_global_rate_limiter=build_global_rate_limiter_func,
        finalize_backfill_status=finalize_backfill_status_func,
        enqueue_compensation_target=partial(
            enqueue_compensation_target_func,
            deps=compensation_deps,
        ),
        auto_trigger_evaluator_best_effort=partial(
            auto_trigger_evaluator_best_effort_func,
            deps=trigger_deps,
        ),
        maybe_trigger_candidate_vetting_check=partial(
            maybe_trigger_candidate_vetting_check_func,
            deps=trigger_deps,
        ),
        mark_crawl_attempt=mark_crawl_attempt_func,
        mark_backfill_running=mark_backfill_running_func,
        mark_backfill_status_only=mark_backfill_status_only_func,
        patrol_target_time_budget_seconds=patrol_target_time_budget_seconds,
    )


async def run_execute_target_task(
    *,
    target_id: str,
    build_execute_target_workflow_deps_func: Any,
    execute_target_workflow_func: Any,
) -> dict[str, object]:
    runtime_input = ExecuteTargetTaskRuntimeInput(target_id=target_id)
    deps = build_execute_target_workflow_deps_func()
    result: ExecuteTargetWorkflowResult = await execute_target_workflow_func(
        target_id=runtime_input.target_id,
        deps=deps,
    )
    return result.as_dict()
