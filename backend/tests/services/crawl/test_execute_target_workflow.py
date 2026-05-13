from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.services.crawl.execute_target_workflow import (
    ExecuteTargetWorkflowDeps,
    execute_target_workflow,
)


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _MappingsResult:
    def __init__(self, row: Any) -> None:
        self._row = row

    def mappings(self) -> "_MappingsResult":
        return self

    def first(self) -> Any:
        return self._row


class _FakeSession:
    def __init__(self) -> None:
        self._target_reads = 0

    async def connection(self) -> None:
        return None

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        sql = str(statement)
        if "to_regclass('public.crawler_run_targets')" in sql:
            return _ScalarResult("crawler_run_targets")
        if "FROM crawler_run_targets" in sql:
            self._target_reads += 1
            return _MappingsResult(None)
        raise AssertionError(f"unexpected SQL: {sql} params={params}")


@asynccontextmanager
async def _session_factory() -> AsyncIterator[_FakeSession]:
    yield _FakeSession()


def _build_dummy_deps(*, audit_calls: list[dict[str, Any]]) -> ExecuteTargetWorkflowDeps:
    async def _noop_async(*args: Any, **kwargs: Any) -> Any:
        return None

    async def _false_async(*args: Any, **kwargs: Any) -> bool:
        return False

    async def _audit_missing_target(*, session: Any, target_id: str, attempts: int) -> None:
        audit_calls.append({"target_id": target_id, "attempts": attempts})

    async def _apply_session_change(
        session: Any,
        *,
        context: str,
        change: Any,
    ) -> bool:
        await change()
        return True

    class _DummyRedditClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

    return ExecuteTargetWorkflowDeps(
        session_factory=_session_factory,
        settings_factory=lambda: object(),
        reddit_client_cls=_DummyRedditClient,
        execute_crawl_plan=_noop_async,
        parse_uuid=lambda value: value,
        ensure_dict=lambda value: value if isinstance(value, dict) else {},
        audit_missing_target=_audit_missing_target,
        rollback_session_quietly=_noop_async,
        commit_session=_false_async,
        apply_session_change=_apply_session_change,
        set_target_failed=_false_async,
        set_target_partial=_false_async,
        set_target_completed=_false_async,
        load_community_blacklist_status=_noop_async,
        needs_community_lock=lambda _: False,
        try_acquire_community_lock=_false_async,
        release_community_lock=_noop_async,
        build_global_rate_limiter=lambda **_: None,
        finalize_backfill_status=_noop_async,
        enqueue_compensation_target=_noop_async,
        auto_trigger_evaluator_best_effort=lambda **_: None,
        maybe_trigger_candidate_vetting_check=lambda **_: None,
        mark_crawl_attempt=_noop_async,
        mark_backfill_running=_noop_async,
        mark_backfill_status_only=_noop_async,
        patrol_target_time_budget_seconds=120.0,
    )


@pytest.mark.asyncio
async def test_execute_target_workflow_missing_target_audits_and_fails() -> None:
    audit_calls: list[dict[str, Any]] = []
    deps = _build_dummy_deps(audit_calls=audit_calls)

    result = await execute_target_workflow(target_id="missing-target", deps=deps)

    assert result.as_dict() == {
        "status": "failed",
        "reason": "target_missing",
        "target_id": "missing-target",
    }
    assert audit_calls == [{"target_id": "missing-target", "attempts": 3}]
