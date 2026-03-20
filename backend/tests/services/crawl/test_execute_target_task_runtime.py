from __future__ import annotations

import pytest

from app.services.crawl.compensation_target_service import CompensationTargetDeps
from app.services.crawl.execute_target_task_runtime import (
    build_execute_target_workflow_deps,
    run_execute_target_task,
)
from app.services.crawl.execute_target_trigger_service import ExecuteTargetTriggerDeps
from app.services.crawl.execute_target_workflow import ExecuteTargetWorkflowResult


@pytest.mark.asyncio
async def test_build_execute_target_workflow_deps_injects_partial_deps() -> None:
    compensation_deps = CompensationTargetDeps(
        settings_factory=lambda: None,
        ensure_dict=lambda value: {},
        ensure_crawler_run_target=lambda *args, **kwargs: None,
        enqueue_target_outbox=lambda *args, **kwargs: None,
        compensation_queue="compensation",
        backfill_posts_queue="backfill",
    )
    trigger_deps = ExecuteTargetTriggerDeps(
        send_task=lambda *args, **kwargs: None,
        env_get=lambda name, default=None: default,
        probe_queue="probe",
        backfill_posts_queue="backfill",
    )
    captured: dict[str, object] = {}

    async def fake_enqueue_compensation_target(*, deps, **kwargs) -> None:  # type: ignore[no-untyped-def]
        captured["compensation"] = deps

    async def fake_auto_trigger(*, deps, **kwargs) -> None:  # type: ignore[no-untyped-def]
        captured["auto"] = deps

    async def fake_vetting_trigger(*, deps, **kwargs) -> None:  # type: ignore[no-untyped-def]
        captured["vetting"] = deps

    deps = build_execute_target_workflow_deps(
        session_factory=lambda: None,
        settings_factory=lambda: None,
        reddit_client_cls=object,
        execute_crawl_plan_func=lambda *args, **kwargs: None,
        parse_uuid_func=lambda value: value,
        ensure_dict_func=lambda value: {},
        audit_missing_target_func=lambda *args, **kwargs: None,
        rollback_session_quietly_func=lambda *args, **kwargs: None,
        commit_session_func=lambda *args, **kwargs: None,
        apply_session_change_func=lambda *args, **kwargs: None,
        set_target_failed_func=lambda *args, **kwargs: None,
        set_target_partial_func=lambda *args, **kwargs: None,
        set_target_completed_func=lambda *args, **kwargs: None,
        load_community_blacklist_status_func=lambda *args, **kwargs: None,
        needs_community_lock_func=lambda *args, **kwargs: False,
        try_acquire_community_lock_func=lambda *args, **kwargs: True,
        release_community_lock_func=lambda *args, **kwargs: None,
        build_global_rate_limiter_func=lambda *args, **kwargs: None,
        finalize_backfill_status_func=lambda *args, **kwargs: None,
        build_compensation_target_deps_func=lambda: compensation_deps,
        enqueue_compensation_target_func=fake_enqueue_compensation_target,
        build_trigger_deps_func=lambda: trigger_deps,
        auto_trigger_evaluator_best_effort_func=fake_auto_trigger,
        maybe_trigger_candidate_vetting_check_func=fake_vetting_trigger,
        mark_crawl_attempt_func=lambda *args, **kwargs: None,
        mark_backfill_running_func=lambda *args, **kwargs: None,
        mark_backfill_status_only_func=lambda *args, **kwargs: None,
        patrol_target_time_budget_seconds=12.0,
    )

    await deps.enqueue_compensation_target(session=None, plan=None, execute_result={})
    await deps.auto_trigger_evaluator_best_effort(
        session=None,
        target_row={},
        outcome={},
        logger=None,
    )
    await deps.maybe_trigger_candidate_vetting_check(
        session=None,
        target_row={},
        outcome={},
        logger=None,
    )

    assert captured["compensation"] is compensation_deps
    assert captured["auto"] is trigger_deps
    assert captured["vetting"] is trigger_deps
    assert deps.patrol_target_time_budget_seconds == 12.0


@pytest.mark.asyncio
async def test_run_execute_target_task_uses_built_deps() -> None:
    sentinel_deps = object()
    captured: dict[str, object] = {}

    def fake_build_execute_target_workflow_deps():  # type: ignore[no-untyped-def]
        captured["deps_built"] = True
        return sentinel_deps

    async def fake_execute_target_workflow(*, target_id, deps):  # type: ignore[no-untyped-def]
        captured["target_id"] = target_id
        captured["deps"] = deps
        return ExecuteTargetWorkflowResult(payload={"status": "completed"})

    result = await run_execute_target_task(
        target_id="abc",
        build_execute_target_workflow_deps_func=fake_build_execute_target_workflow_deps,
        execute_target_workflow_func=fake_execute_target_workflow,
    )

    assert captured["deps_built"] is True
    assert captured["target_id"] == "abc"
    assert captured["deps"] is sentinel_deps
    assert result == {"status": "completed"}
