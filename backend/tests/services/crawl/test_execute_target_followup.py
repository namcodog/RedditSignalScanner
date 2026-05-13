from __future__ import annotations

from typing import Any

import pytest

from app.services.crawl.execute_target_followup import (
    ExecuteTargetFollowupDeps,
    ExecuteTargetFollowupInput,
    finalize_execute_target_outcome,
)
from app.services.crawl.plan_contract import CrawlPlanContract


def _plan(*, plan_kind: str = "patrol", budget_cap: bool = False) -> CrawlPlanContract:
    meta = {"budget_cap": budget_cap}
    target_type = "subreddit"
    target_value = "r/demo"
    limits: dict[str, int] = {}
    if plan_kind == "probe":
        meta["source"] = "search"
        target_type = "query"
        target_value = "wireless earbuds"
        limits = {"posts_limit": 25}
    return CrawlPlanContract(
        plan_kind=plan_kind,
        target_type=target_type,
        target_value=target_value,
        reason="test",
        limits=limits,
        meta=meta,
    )


def _deps(
    *,
    calls: dict[str, Any],
    complete_ok: bool = True,
) -> ExecuteTargetFollowupDeps:
    async def _finalize_backfill_status(**kwargs: Any) -> None:
        calls.setdefault("finalize", []).append(kwargs)

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

    async def _set_target_completed(
        _session: Any,
        *,
        community_run_id: str,
        metrics: dict[str, Any],
        context: str,
    ) -> bool:
        calls.setdefault("completed", []).append(
            {
                "community_run_id": community_run_id,
                "metrics": metrics,
                "context": context,
            }
        )
        return complete_ok

    async def _enqueue_compensation_target(**kwargs: Any) -> str | None:
        calls.setdefault("compensation", []).append(kwargs)
        return "comp-123"

    def _auto_trigger_evaluator_best_effort(**kwargs: Any) -> None:
        calls.setdefault("evaluator", []).append(kwargs)

    def _maybe_trigger_candidate_vetting_check(**kwargs: Any) -> None:
        calls.setdefault("vetting", []).append(kwargs)

    return ExecuteTargetFollowupDeps(
        finalize_backfill_status=_finalize_backfill_status,
        commit_session=_commit_session,
        rollback_session_quietly=_rollback_session_quietly,
        set_target_partial=_set_target_partial,
        set_target_completed=_set_target_completed,
        enqueue_compensation_target=_enqueue_compensation_target,
        auto_trigger_evaluator_best_effort=_auto_trigger_evaluator_best_effort,
        maybe_trigger_candidate_vetting_check=_maybe_trigger_candidate_vetting_check,
    )


@pytest.mark.asyncio
async def test_finalize_execute_target_outcome_returns_probe_partial_without_compensation() -> None:
    calls: dict[str, Any] = {}
    result = await finalize_execute_target_outcome(
        followup_input=ExecuteTargetFollowupInput(
            session=object(),
            crawl_run_id="run-1",
            target_id="target-1",
            subreddit="r/demo",
            plan=_plan(plan_kind="probe"),
            outcome={"status": "partial", "reason": "cursor_remaining"},
            base_idempotency_key="base-1",
        ),
        deps=_deps(calls=calls),
    )

    assert result.payload["status"] == "partial"
    assert result.payload["reason"] == "cursor_remaining"
    assert result.payload["compensation_target_id"] is None
    assert "compensation" not in calls
    assert len(calls.get("partial", [])) == 1
    assert len(calls.get("evaluator", [])) == 1
    assert "vetting" not in calls


@pytest.mark.asyncio
async def test_finalize_execute_target_outcome_marks_completed_and_triggers_followups() -> None:
    calls: dict[str, Any] = {}
    result = await finalize_execute_target_outcome(
        followup_input=ExecuteTargetFollowupInput(
            session=object(),
            crawl_run_id="run-2",
            target_id="target-2",
            subreddit="r/demo",
            plan=_plan(plan_kind="patrol"),
            outcome={"status": "completed", "items_api_returned": 12},
            base_idempotency_key="base-2",
        ),
        deps=_deps(calls=calls),
    )

    assert result.payload["status"] == "completed"
    assert result.payload["crawl_run_id"] == "run-2"
    assert len(calls.get("completed", [])) == 1
    assert len(calls.get("evaluator", [])) == 1
    assert len(calls.get("vetting", [])) == 1
