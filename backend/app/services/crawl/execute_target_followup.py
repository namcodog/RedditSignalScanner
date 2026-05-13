from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any

from app.services.crawl.plan_contract import CrawlPlanContract


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ExecuteTargetFollowupInput:
    session: Any
    crawl_run_id: str
    target_id: str
    subreddit: str
    plan: CrawlPlanContract
    outcome: dict[str, object]
    base_idempotency_key: str


@dataclass(slots=True, frozen=True)
class ExecuteTargetFollowupDeps:
    finalize_backfill_status: Callable[..., Awaitable[None]]
    commit_session: Callable[..., Awaitable[bool]]
    rollback_session_quietly: Callable[..., Awaitable[None]]
    set_target_partial: Callable[..., Awaitable[bool]]
    set_target_completed: Callable[..., Awaitable[bool]]
    enqueue_compensation_target: Callable[..., Awaitable[str | None]]
    auto_trigger_evaluator_best_effort: Callable[..., None]
    maybe_trigger_candidate_vetting_check: Callable[..., None]


@dataclass(slots=True, frozen=True)
class ExecuteTargetFollowupResult:
    payload: dict[str, object]


def _result(**payload: object) -> ExecuteTargetFollowupResult:
    return ExecuteTargetFollowupResult(payload=dict(payload))


async def finalize_execute_target_outcome(
    *,
    followup_input: ExecuteTargetFollowupInput,
    deps: ExecuteTargetFollowupDeps,
) -> ExecuteTargetFollowupResult:
    session = followup_input.session
    plan = followup_input.plan
    outcome = followup_input.outcome
    subreddit = followup_input.subreddit
    target_id = followup_input.target_id
    crawl_run_id = followup_input.crawl_run_id

    if plan.plan_kind == "backfill_posts":
        try:
            await deps.finalize_backfill_status(
                session=session,
                subreddit=plan.target_value,
                plan=plan,
                outcome=outcome,
            )
            await deps.commit_session(session, context="finalize_backfill_status")
        except Exception as exc:
            logger.warning(
                "Failed to finalize backfill status for %s: %s",
                plan.target_value,
                exc,
                exc_info=exc,
            )
            await deps.rollback_session_quietly(
                session,
                context="finalize_backfill_status",
            )

    if str(outcome.get("status") or "") == "partial":
        reason = str(outcome.get("reason") or "partial")
        cursor_after = str(outcome.get("cursor_after") or "") or None
        await deps.set_target_partial(
            session,
            community_run_id=target_id,
            error_code=reason,
            error_message_short=str(outcome.get("error") or reason)[:400],
            metrics=dict(outcome),
            context=f"outcome_partial:{reason}",
        )

        if bool(plan.meta.get("budget_cap")) and reason == "cursor_remaining":
            deps.maybe_trigger_candidate_vetting_check(plan=plan)
            return _result(
                status="partial",
                reason=reason,
                crawl_run_id=crawl_run_id,
                target_id=target_id,
                community_run_id=target_id,
                subreddit=subreddit,
                plan_kind=plan.plan_kind,
                compensation_target_id=None,
            )

        if plan.plan_kind == "probe":
            deps.auto_trigger_evaluator_best_effort(
                plan=plan,
                outcome=dict(outcome),
            )
            return _result(
                status="partial",
                reason=reason,
                crawl_run_id=crawl_run_id,
                target_id=target_id,
                community_run_id=target_id,
                subreddit=subreddit,
                plan_kind=plan.plan_kind,
                compensation_target_id=None,
            )

        try:
            comp_target_id = await deps.enqueue_compensation_target(
                session=session,
                crawl_run_id=crawl_run_id,
                subreddit=subreddit,
                original_target_id=target_id,
                plan=plan,
                base_idempotency_key=followup_input.base_idempotency_key,
                reason=reason,
                cursor_after=cursor_after,
            )
            await deps.commit_session(
                session,
                context=f"partial_compensation:{reason}",
            )
        except Exception as exc:
            logger.warning(
                "Failed to enqueue partial compensation for %s (%s): %s",
                subreddit,
                reason,
                exc,
                exc_info=exc,
            )
            await deps.rollback_session_quietly(
                session,
                context=f"partial_compensation:{reason}",
            )
            comp_target_id = None

        return _result(
            status="partial",
            reason=reason,
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            plan_kind=plan.plan_kind,
            compensation_target_id=comp_target_id,
        )

    if not await deps.set_target_completed(
        session,
        community_run_id=target_id,
        metrics=dict(outcome),
        context="complete_target",
    ):
        return _result(
            status="failed",
            reason="complete_persist_failed",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            plan_kind=plan.plan_kind,
        )

    result = dict(outcome)
    result.setdefault("crawl_run_id", crawl_run_id)
    result.setdefault("target_id", target_id)
    result.setdefault("community_run_id", target_id)
    result.setdefault("subreddit", subreddit)
    result.setdefault("plan_kind", plan.plan_kind)
    deps.auto_trigger_evaluator_best_effort(plan=plan, outcome=dict(outcome))
    deps.maybe_trigger_candidate_vetting_check(plan=plan)
    return ExecuteTargetFollowupResult(payload=result)


__all__ = [
    "ExecuteTargetFollowupDeps",
    "ExecuteTargetFollowupInput",
    "ExecuteTargetFollowupResult",
    "finalize_execute_target_outcome",
]
