from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.crawl.execute_target_trigger_service import (
    ExecuteTargetTriggerDeps,
    auto_trigger_evaluator_best_effort,
    maybe_trigger_candidate_vetting_check,
    should_auto_trigger_evaluator,
)
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanWindow


def _plan(*, plan_kind: str = "probe", reason: str = "user_query", target_value: str = "demo") -> CrawlPlanContract:
    target_type = "query" if plan_kind == "probe" else "subreddit"
    meta = {"source": "search"} if plan_kind == "probe" else {}
    window = None
    if plan_kind == "backfill_posts":
        now = datetime.now(timezone.utc)
        window = CrawlPlanWindow(since=now, until=now + timedelta(seconds=1))
    return CrawlPlanContract(
        plan_kind=plan_kind,
        target_type=target_type,
        target_value=target_value,
        reason=reason,
        window=window,
        limits={"posts_limit": 10},
        meta=meta,
    )


def _deps(
    *,
    sent: list[dict[str, Any]],
    auto_enabled: str = "1",
) -> ExecuteTargetTriggerDeps:
    def _send_task(task_name: str, *args: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    return ExecuteTargetTriggerDeps(
        send_task=_send_task,
        env_get=lambda name, default: auto_enabled if name == "PROBE_AUTO_EVALUATE_ENABLED" else default,
        probe_queue="probe_queue",
        backfill_posts_queue="backfill_posts_queue_v2",
    )


def test_should_auto_trigger_evaluator_only_for_probe_with_discovered_rows() -> None:
    deps = _deps(sent=[])

    assert should_auto_trigger_evaluator(
        plan=_plan(plan_kind="probe"),
        outcome={"discovered_communities_upserted": 2},
        deps=deps,
    ) is True
    assert should_auto_trigger_evaluator(
        plan=_plan(plan_kind="probe"),
        outcome={"discovered_communities_upserted": 0},
        deps=deps,
    ) is False
    assert should_auto_trigger_evaluator(
        plan=_plan(plan_kind="patrol", reason="cache_expired", target_value="r/demo"),
        outcome={"discovered_communities_upserted": 2},
        deps=deps,
    ) is False


def test_auto_trigger_evaluator_best_effort_respects_env_gate() -> None:
    sent: list[dict[str, Any]] = []
    auto_trigger_evaluator_best_effort(
        plan=_plan(plan_kind="probe"),
        outcome={"discovered_communities_upserted": 3},
        deps=_deps(sent=sent, auto_enabled="0"),
    )
    assert sent == []


def test_maybe_trigger_candidate_vetting_check_only_for_candidate_vetting_backfill() -> None:
    sent: list[dict[str, Any]] = []
    maybe_trigger_candidate_vetting_check(
        plan=_plan(
            plan_kind="backfill_posts",
            reason="candidate_vetting",
            target_value="r/candidate_demo",
        ),
        deps=_deps(sent=sent),
    )

    assert len(sent) == 1
    assert sent[0]["task_name"] == "tasks.discovery.check_candidate_vetting"
    assert sent[0]["kwargs"]["kwargs"]["community"] == "r/candidate_demo"
    assert sent[0]["kwargs"]["queue"] == "backfill_posts_queue_v2"

    sent.clear()
    maybe_trigger_candidate_vetting_check(
        plan=_plan(plan_kind="backfill_posts", reason="bootstrap_backfill", target_value="r/demo"),
        deps=_deps(sent=sent),
    )
    assert sent == []
