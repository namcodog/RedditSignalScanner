from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.services.crawl.execute_target_error_workflow import (
    ExecuteTargetErrorDeps,
    ExecuteTargetErrorInput,
    finalize_execute_target_error,
)
from app.services.crawl.plan_contract import CrawlPlanContract


def _plan(*, plan_kind: str = "patrol", target_type: str = "subreddit") -> CrawlPlanContract:
    target_value = "r/demo" if target_type == "subreddit" else "wireless earbuds"
    limits: dict[str, int] = {}
    meta: dict[str, object] = {}
    window: dict[str, str] | None = None
    if plan_kind == "probe":
        target_type = "query"
        target_value = "wireless earbuds"
        limits = {"posts_limit": 25}
        meta = {"source": "search"}
    elif plan_kind == "backfill_posts":
        now = datetime.now(timezone.utc)
        window = {
            "since": (now - timedelta(days=7)).isoformat(),
            "until": now.isoformat(),
        }
    return CrawlPlanContract(
        plan_kind=plan_kind,
        target_type=target_type,
        target_value=target_value,
        reason="test",
        window=window,
        limits=limits,
        meta=meta,
    )


def _deps(calls: dict[str, Any]) -> ExecuteTargetErrorDeps:
    async def _mark_crawl_attempt(*args: Any, **kwargs: Any) -> None:
        calls.setdefault("mark_attempt", []).append((args, kwargs))

    async def _mark_backfill_status_only(*args: Any, **kwargs: Any) -> None:
        calls.setdefault("backfill_status", []).append((args, kwargs))

    async def _commit_session(_session: Any, *, context: str) -> bool:
        calls.setdefault("commit", []).append(context)
        return True

    async def _rollback_session_quietly(_session: Any, *, context: str) -> None:
        calls.setdefault("rollback", []).append(context)

    async def _set_target_partial(
        _session: Any,
        *,
        community_run_id: str,
        error_code: str,
        error_message_short: str,
        metrics: dict[str, Any],
        context: str,
    ) -> bool:
        calls.setdefault("partial", []).append(
            {
                "community_run_id": community_run_id,
                "error_code": error_code,
                "error_message_short": error_message_short,
                "metrics": metrics,
                "context": context,
            }
        )
        return True

    async def _set_target_failed(
        _session: Any,
        *,
        community_run_id: str,
        error_code: str,
        error_message_short: str,
        context: str,
    ) -> bool:
        calls.setdefault("failed", []).append(
            {
                "community_run_id": community_run_id,
                "error_code": error_code,
                "error_message_short": error_message_short,
                "context": context,
            }
        )
        return True

    async def _enqueue_compensation_target(**kwargs: Any) -> str | None:
        calls.setdefault("compensation", []).append(kwargs)
        return "comp-123"

    return ExecuteTargetErrorDeps(
        mark_crawl_attempt=_mark_crawl_attempt,
        mark_backfill_status_only=_mark_backfill_status_only,
        commit_session=_commit_session,
        rollback_session_quietly=_rollback_session_quietly,
        set_target_partial=_set_target_partial,
        set_target_failed=_set_target_failed,
        enqueue_compensation_target=_enqueue_compensation_target,
    )


@pytest.mark.asyncio
async def test_finalize_execute_target_error_timeout_marks_partial_and_compensation() -> None:
    calls: dict[str, Any] = {}

    result = await finalize_execute_target_error(
        error_input=ExecuteTargetErrorInput(
            session=object(),
            crawl_run_id="run-timeout",
            target_id="target-timeout",
            subreddit="r/demo",
            plan=_plan(plan_kind="patrol"),
            base_idempotency_key="base-timeout",
            reason="timeout",
            timeout_seconds=30.0,
        ),
        deps=_deps(calls),
    )

    assert result.payload["status"] == "partial"
    assert result.payload["reason"] == "timeout"
    assert result.payload["compensation_target_id"] == "comp-123"
    assert calls["rollback"] == ["timeout_before_partial"]
    assert calls["commit"] == ["timeout_compensation"]
    assert calls["partial"][0]["metrics"]["stop_reason"] == "timeout"
    assert calls["compensation"][0]["countdown_seconds"] == 60
    assert len(calls["mark_attempt"]) == 1


@pytest.mark.asyncio
async def test_finalize_execute_target_error_budget_exhausted_updates_backfill_and_partial() -> None:
    calls: dict[str, Any] = {}

    result = await finalize_execute_target_error(
        error_input=ExecuteTargetErrorInput(
            session=object(),
            crawl_run_id="run-budget",
            target_id="target-budget",
            subreddit="r/demo",
            plan=_plan(plan_kind="backfill_posts"),
            base_idempotency_key="base-budget",
            reason="budget_exhausted",
            wait_seconds=45,
        ),
        deps=_deps(calls),
    )

    assert result.payload["status"] == "partial"
    assert result.payload["reason"] == "budget_exhausted"
    assert calls["commit"] == ["mark_backfill_budget_exhausted", "budget_exhausted_compensation"]
    assert calls["partial"][0]["metrics"]["wait_seconds"] == 45
    assert len(calls["backfill_status"]) == 1
    assert calls["compensation"][0]["countdown_seconds"] == 45


@pytest.mark.asyncio
async def test_finalize_execute_target_error_execute_failed_marks_failed_without_compensation() -> None:
    calls: dict[str, Any] = {}

    result = await finalize_execute_target_error(
        error_input=ExecuteTargetErrorInput(
            session=object(),
            crawl_run_id="run-failed",
            target_id="target-failed",
            subreddit="r/demo",
            plan=_plan(plan_kind="backfill_posts"),
            base_idempotency_key="base-failed",
            reason="execute_failed",
            error_message="boom",
        ),
        deps=_deps(calls),
    )

    assert result.payload["status"] == "failed"
    assert result.payload["reason"] == "execute_failed"
    assert calls["commit"] == ["mark_backfill_execute_failed"]
    assert len(calls["failed"]) == 1
    assert "compensation" not in calls
