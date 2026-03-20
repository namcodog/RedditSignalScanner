from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any

from app.services.crawl.plan_contract import CrawlPlanContract


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ExecuteTargetErrorInput:
    session: Any
    crawl_run_id: str
    target_id: str
    subreddit: str
    plan: CrawlPlanContract
    base_idempotency_key: str
    reason: str
    error_message: str | None = None
    timeout_seconds: float | None = None
    wait_seconds: int | None = None


@dataclass(slots=True, frozen=True)
class ExecuteTargetErrorDeps:
    mark_crawl_attempt: Callable[..., Awaitable[None]]
    mark_backfill_status_only: Callable[..., Awaitable[None]]
    commit_session: Callable[..., Awaitable[bool]]
    rollback_session_quietly: Callable[..., Awaitable[None]]
    set_target_partial: Callable[..., Awaitable[bool]]
    set_target_failed: Callable[..., Awaitable[bool]]
    enqueue_compensation_target: Callable[..., Awaitable[str | None]]


@dataclass(slots=True, frozen=True)
class ExecuteTargetErrorResult:
    payload: dict[str, object]


def _result(**payload: object) -> ExecuteTargetErrorResult:
    return ExecuteTargetErrorResult(payload=dict(payload))


async def finalize_execute_target_error(
    *,
    error_input: ExecuteTargetErrorInput,
    deps: ExecuteTargetErrorDeps,
) -> ExecuteTargetErrorResult:
    session = error_input.session
    plan = error_input.plan
    subreddit = error_input.subreddit
    target_id = error_input.target_id
    crawl_run_id = error_input.crawl_run_id
    reason = error_input.reason

    if plan.target_type == "subreddit":
        try:
            await deps.mark_crawl_attempt(plan.target_value, session=session)
        except Exception as exc:
            logger.warning(
                "Failed to mark crawl attempt for %s (%s): %s",
                plan.target_value,
                reason,
                exc,
                exc_info=exc,
            )

    if plan.plan_kind == "backfill_posts":
        try:
            await deps.mark_backfill_status_only(
                plan.target_value,
                status="ERROR",
                session=session,
            )
            await deps.commit_session(
                session,
                context=f"mark_backfill_{reason}",
            )
        except Exception as exc:
            logger.warning(
                "Failed to mark backfill %s for %s: %s",
                reason,
                plan.target_value,
                exc,
                exc_info=exc,
            )
            await deps.rollback_session_quietly(
                session,
                context=f"mark_backfill_{reason}",
            )

    if reason == "execute_failed":
        await deps.set_target_failed(
            session,
            community_run_id=target_id,
            error_code="execute_failed",
            error_message_short=str(error_input.error_message or "execute_failed")[:400],
            context="execute_failed",
        )
        return _result(
            status="failed",
            reason="execute_failed",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            plan_kind=plan.plan_kind,
        )

    await deps.rollback_session_quietly(
        session,
        context=f"{reason}_before_partial",
    )

    metrics: dict[str, object]
    error_message_short: str
    countdown_seconds: int | None

    if reason == "timeout":
        metrics = {
            "error": "timeout",
            "timeout_seconds": error_input.timeout_seconds,
            "plan_kind": plan.plan_kind,
            "metrics_schema_version": 2,
            "stop_reason": "timeout",
            "partial_reason": "timeout",
            "api_calls_total": 0,
            "pages_processed": 0,
            "items_api_returned": 0,
        }
        error_message_short = "patrol target timed out"
        countdown_seconds = 60
    elif reason == "budget_exhausted":
        metrics = {
            "error": "budget_exhausted",
            "wait_seconds": int(error_input.wait_seconds or 0),
            "plan_kind": plan.plan_kind,
        }
        error_message_short = "global token bucket exhausted"
        countdown_seconds = int(error_input.wait_seconds or 0)
    else:
        raise ValueError(f"Unsupported execute target error reason: {reason}")

    await deps.set_target_partial(
        session,
        community_run_id=target_id,
        error_code=reason,
        error_message_short=error_message_short,
        metrics=metrics,
        context=f"{reason}_partial",
    )

    comp_target_id = None
    if plan.plan_kind != "probe":
        try:
            comp_target_id = await deps.enqueue_compensation_target(
                session=session,
                crawl_run_id=crawl_run_id,
                subreddit=subreddit,
                original_target_id=target_id,
                plan=plan,
                base_idempotency_key=error_input.base_idempotency_key,
                reason=reason,
                countdown_seconds=countdown_seconds,
            )
            await deps.commit_session(
                session,
                context=f"{reason}_compensation",
            )
        except Exception as exc:
            logger.warning(
                "Failed to enqueue %s compensation for %s: %s",
                reason,
                subreddit,
                exc,
                exc_info=exc,
            )
            await deps.rollback_session_quietly(
                session,
                context=f"{reason}_compensation",
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


__all__ = [
    "ExecuteTargetErrorDeps",
    "ExecuteTargetErrorInput",
    "ExecuteTargetErrorResult",
    "finalize_execute_target_error",
]
