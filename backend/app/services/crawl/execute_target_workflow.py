from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
import time
from typing import Any

from app.services.crawl.execute_target_error_workflow import (
    ExecuteTargetErrorDeps,
    ExecuteTargetErrorInput,
    finalize_execute_target_error,
)
from app.services.crawl.execute_target_followup import (
    ExecuteTargetFollowupDeps,
    ExecuteTargetFollowupInput,
    finalize_execute_target_outcome,
)
from app.services.crawl.execute_target_preflight import (
    ExecuteTargetPreflightDeps,
    ExecuteTargetPreflightInput,
    prepare_execute_target_preflight,
)
from app.services.infrastructure.reddit_client import RedditGlobalRateLimitExceeded

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ExecuteTargetWorkflowResult:
    payload: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return dict(self.payload)


@dataclass(slots=True, frozen=True)
class ExecuteTargetWorkflowDeps:
    session_factory: Callable[[], Any]
    settings_factory: Callable[[], Any]
    reddit_client_cls: type[Any]
    execute_crawl_plan: Callable[..., Awaitable[dict[str, object]]]
    parse_uuid: Callable[[str], str]
    ensure_dict: Callable[[object], dict[str, Any]]
    audit_missing_target: Callable[..., Awaitable[None]]
    rollback_session_quietly: Callable[..., Awaitable[None]]
    commit_session: Callable[..., Awaitable[bool]]
    apply_session_change: Callable[..., Awaitable[bool]]
    set_target_failed: Callable[..., Awaitable[bool]]
    set_target_partial: Callable[..., Awaitable[bool]]
    set_target_completed: Callable[..., Awaitable[bool]]
    load_community_blacklist_status: Callable[..., Awaitable[bool | None]]
    needs_community_lock: Callable[[str], bool]
    try_acquire_community_lock: Callable[..., Awaitable[bool]]
    release_community_lock: Callable[..., Awaitable[None]]
    build_global_rate_limiter: Callable[..., Any]
    finalize_backfill_status: Callable[..., Awaitable[None]]
    enqueue_compensation_target: Callable[..., Awaitable[str | None]]
    auto_trigger_evaluator_best_effort: Callable[..., None]
    maybe_trigger_candidate_vetting_check: Callable[..., None]
    mark_crawl_attempt: Callable[..., Awaitable[None]]
    mark_backfill_running: Callable[..., Awaitable[None]]
    mark_backfill_status_only: Callable[..., Awaitable[None]]
    patrol_target_time_budget_seconds: float


def _result(**payload: object) -> ExecuteTargetWorkflowResult:
    return ExecuteTargetWorkflowResult(payload=dict(payload))


async def execute_target_workflow(
    *,
    target_id: str,
    deps: ExecuteTargetWorkflowDeps,
) -> ExecuteTargetWorkflowResult:
    normalized_id = deps.parse_uuid(target_id)
    settings = deps.settings_factory()

    async with deps.session_factory() as session:
        await session.connection()
        preflight_result = await prepare_execute_target_preflight(
            preflight_input=ExecuteTargetPreflightInput(
                session=session,
                target_id=normalized_id,
            ),
            deps=ExecuteTargetPreflightDeps(
                ensure_dict=deps.ensure_dict,
                audit_missing_target=deps.audit_missing_target,
                apply_session_change=deps.apply_session_change,
                commit_session=deps.commit_session,
                rollback_session_quietly=deps.rollback_session_quietly,
                set_target_failed=deps.set_target_failed,
                set_target_partial=deps.set_target_partial,
                load_community_blacklist_status=deps.load_community_blacklist_status,
                needs_community_lock=deps.needs_community_lock,
                try_acquire_community_lock=deps.try_acquire_community_lock,
                enqueue_compensation_target=deps.enqueue_compensation_target,
                mark_backfill_running=deps.mark_backfill_running,
            ),
        )
        if preflight_result.early_payload is not None:
            return ExecuteTargetWorkflowResult(payload=preflight_result.early_payload)

        preflight = preflight_result.context
        assert preflight is not None
        crawl_run_id = preflight.crawl_run_id
        subreddit = preflight.subreddit
        existing_metrics = preflight.existing_metrics
        plan = preflight.plan
        base_idempotency_key = preflight.base_idempotency_key
        lock_acquired = preflight.lock_acquired
        lock_target = preflight.lock_target

        global_rate_limiter = deps.build_global_rate_limiter(
            settings=settings,
            plan_kind=str(plan.plan_kind),
        )

        try:
            async with deps.reddit_client_cls(
                settings.reddit_client_id,
                settings.reddit_client_secret,
                settings.reddit_user_agent,
                rate_limit=settings.reddit_rate_limit,
                rate_limit_window=settings.reddit_rate_limit_window_seconds,
                request_timeout=settings.reddit_request_timeout_seconds,
                max_concurrency=settings.reddit_max_concurrency,
                global_rate_limiter=global_rate_limiter,
                fail_fast_on_global_rate_limit=True,
            ) as reddit:
                try:
                    start = time.monotonic()
                    coro = deps.execute_crawl_plan(
                        plan=plan,
                        session=session,
                        reddit_client=reddit,
                        crawl_run_id=crawl_run_id,
                        community_run_id=normalized_id,
                    )
                    if (
                        plan.plan_kind == "patrol"
                        and deps.patrol_target_time_budget_seconds > 0
                    ):
                        outcome = await asyncio.wait_for(
                            coro,
                            timeout=deps.patrol_target_time_budget_seconds,
                        )
                    else:
                        outcome = await coro
                    duration = time.monotonic() - start
                    if isinstance(outcome, dict) and "duration_seconds" not in outcome:
                        outcome["duration_seconds"] = duration
                except asyncio.TimeoutError:
                    error_result = await finalize_execute_target_error(
                        error_input=ExecuteTargetErrorInput(
                            session=session,
                            crawl_run_id=crawl_run_id,
                            target_id=normalized_id,
                            subreddit=subreddit,
                            plan=plan,
                            base_idempotency_key=base_idempotency_key,
                            reason="timeout",
                            timeout_seconds=deps.patrol_target_time_budget_seconds,
                        ),
                        deps=ExecuteTargetErrorDeps(
                            mark_crawl_attempt=deps.mark_crawl_attempt,
                            mark_backfill_status_only=deps.mark_backfill_status_only,
                            commit_session=deps.commit_session,
                            rollback_session_quietly=deps.rollback_session_quietly,
                            set_target_partial=deps.set_target_partial,
                            set_target_failed=deps.set_target_failed,
                            enqueue_compensation_target=deps.enqueue_compensation_target,
                        ),
                    )
                    return ExecuteTargetWorkflowResult(payload=error_result.payload)
                except RedditGlobalRateLimitExceeded as exc:
                    error_result = await finalize_execute_target_error(
                        error_input=ExecuteTargetErrorInput(
                            session=session,
                            crawl_run_id=crawl_run_id,
                            target_id=normalized_id,
                            subreddit=subreddit,
                            plan=plan,
                            base_idempotency_key=base_idempotency_key,
                            reason="budget_exhausted",
                            wait_seconds=int(exc.wait_seconds),
                        ),
                        deps=ExecuteTargetErrorDeps(
                            mark_crawl_attempt=deps.mark_crawl_attempt,
                            mark_backfill_status_only=deps.mark_backfill_status_only,
                            commit_session=deps.commit_session,
                            rollback_session_quietly=deps.rollback_session_quietly,
                            set_target_partial=deps.set_target_partial,
                            set_target_failed=deps.set_target_failed,
                            enqueue_compensation_target=deps.enqueue_compensation_target,
                        ),
                    )
                    return ExecuteTargetWorkflowResult(payload=error_result.payload)
                except Exception as exc:
                    await finalize_execute_target_error(
                        error_input=ExecuteTargetErrorInput(
                            session=session,
                            crawl_run_id=crawl_run_id,
                            target_id=normalized_id,
                            subreddit=subreddit,
                            plan=plan,
                            base_idempotency_key=base_idempotency_key,
                            reason="execute_failed",
                            error_message=str(exc),
                        ),
                        deps=ExecuteTargetErrorDeps(
                            mark_crawl_attempt=deps.mark_crawl_attempt,
                            mark_backfill_status_only=deps.mark_backfill_status_only,
                            commit_session=deps.commit_session,
                            rollback_session_quietly=deps.rollback_session_quietly,
                            set_target_partial=deps.set_target_partial,
                            set_target_failed=deps.set_target_failed,
                            enqueue_compensation_target=deps.enqueue_compensation_target,
                        ),
                    )
                    raise
        finally:
            if lock_acquired and lock_target:
                try:
                    await deps.release_community_lock(
                        session=session,
                        community_name=lock_target,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to release community lock for %s: %s",
                        lock_target,
                        exc,
                        exc_info=exc,
                    )

        followup_result = await finalize_execute_target_outcome(
            followup_input=ExecuteTargetFollowupInput(
                session=session,
                crawl_run_id=crawl_run_id,
                target_id=normalized_id,
                subreddit=subreddit,
                plan=plan,
                outcome=dict(outcome) if isinstance(outcome, dict) else {},
                base_idempotency_key=base_idempotency_key,
            ),
            deps=ExecuteTargetFollowupDeps(
                finalize_backfill_status=deps.finalize_backfill_status,
                commit_session=deps.commit_session,
                rollback_session_quietly=deps.rollback_session_quietly,
                set_target_partial=deps.set_target_partial,
                set_target_completed=deps.set_target_completed,
                enqueue_compensation_target=deps.enqueue_compensation_target,
                auto_trigger_evaluator_best_effort=deps.auto_trigger_evaluator_best_effort,
                maybe_trigger_candidate_vetting_check=deps.maybe_trigger_candidate_vetting_check,
            ),
        )
        return ExecuteTargetWorkflowResult(payload=followup_result.payload)


__all__ = [
    "ExecuteTargetWorkflowDeps",
    "ExecuteTargetWorkflowResult",
    "execute_target_workflow",
]
