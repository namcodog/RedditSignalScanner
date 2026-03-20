from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
import os
from typing import Any

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.community.community_cache_service import (
    mark_crawl_attempt,
    mark_backfill_running,
    mark_backfill_status_only,
    update_backfill_status,
)
from app.services.crawl.execute_plan import execute_crawl_plan
from app.services.crawl.compensation_target_service import (
    CompensationTargetDeps,
    enqueue_compensation_target,
)
from app.services.crawl.execute_target_trigger_service import (
    ExecuteTargetTriggerDeps,
    auto_trigger_evaluator_best_effort,
    maybe_trigger_candidate_vetting_check,
    should_auto_trigger_evaluator,
)
from app.services.crawl.execute_target_task_runtime import (
    build_execute_target_workflow_deps,
    run_execute_target_task,
)
from app.services.crawl.execute_target_task_support import (
    backfill_comments_min,
    backfill_done_months,
    backfill_posts_min,
    build_global_rate_limiter,
    count_comments_since,
    count_posts_since,
    ensure_dict,
    finalize_backfill_status,
    load_backfill_floor,
    load_community_blacklist_status,
    needs_community_lock,
    parse_iso_datetime,
    parse_uuid,
    release_community_lock,
    try_acquire_community_lock,
)
from app.services.crawl.execute_target_workflow import (
    ExecuteTargetWorkflowDeps,
    execute_target_workflow,
)
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.crawl.crawler_run_targets_service import (
    complete_crawler_run_target,
    ensure_crawler_run_target,
    fail_crawler_run_target,
    partial_crawler_run_target,
)
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.utils.asyncio_runner import run as run_coro

logger = get_task_logger(__name__)

PATROL_TARGET_TIME_BUDGET_SECONDS = float(
    os.getenv("PATROL_TARGET_TIME_BUDGET_SECONDS", "120")
)
BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")
COMPENSATION_QUEUE = os.getenv("CRAWLER_COMPENSATION_QUEUE", "compensation_queue")
CRAWLER_GLOBAL_BUCKET_ENABLED = os.getenv("CRAWLER_GLOBAL_BUCKET_ENABLED", "true").lower() not in {
    "0",
    "false",
    "no",
}
LOCKED_PLAN_KINDS = {
    "backfill_posts",
    "seed_top_year",
    "seed_top_all",
    "seed_controversial_year",
}


def _parse_uuid(value: str) -> str:
    return parse_uuid(value)


def _ensure_dict(value: object) -> dict[str, Any]:
    return ensure_dict(value)


async def _audit_missing_target(
    *, session: Any, target_id: str, attempts: int
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO data_audit_events (
                event_type, target_type, target_id, reason, source_component, new_value
            )
            VALUES (
                'execute_target_missing',
                'crawler_run_targets',
                :target_id,
                'not_found',
                'execute_target',
                jsonb_build_object('attempts', :attempts)
            )
            """
        ),
        {"target_id": target_id, "attempts": attempts},
    )


async def _rollback_session_quietly(session: Any, *, context: str) -> None:
    try:
        await session.rollback()
    except Exception as exc:
        logger.warning("Rollback failed during %s: %s", context, exc, exc_info=exc)


async def _commit_session(session: Any, *, context: str) -> bool:
    try:
        await session.commit()
        return True
    except Exception as exc:
        logger.warning("Commit failed during %s: %s", context, exc, exc_info=exc)
        await _rollback_session_quietly(session, context=f"{context}:rollback")
        return False


async def _apply_session_change(
    session: Any,
    *,
    context: str,
    change: Callable[[], Awaitable[None]],
) -> bool:
    try:
        await change()
    except Exception as exc:
        logger.warning("State change failed during %s: %s", context, exc, exc_info=exc)
        await _rollback_session_quietly(session, context=f"{context}:rollback")
        return False
    return await _commit_session(session, context=context)


async def _set_target_failed(
    session: Any,
    *,
    community_run_id: str,
    error_code: str,
    error_message_short: str,
    context: str,
) -> bool:
    async def _change() -> None:
        await fail_crawler_run_target(
            session,
            community_run_id=community_run_id,
            error_code=error_code,
            error_message_short=error_message_short,
        )

    return await _apply_session_change(session, context=context, change=_change)


async def _set_target_partial(
    session: Any,
    *,
    community_run_id: str,
    error_code: str,
    error_message_short: str,
    metrics: dict[str, Any],
    context: str,
) -> bool:
    async def _change() -> None:
        await partial_crawler_run_target(
            session,
            community_run_id=community_run_id,
            error_code=error_code,
            error_message_short=error_message_short,
            metrics=metrics,
        )

    return await _apply_session_change(session, context=context, change=_change)


async def _set_target_completed(
    session: Any,
    *,
    community_run_id: str,
    metrics: dict[str, Any],
    context: str,
) -> bool:
    async def _change() -> None:
        await complete_crawler_run_target(
            session,
            community_run_id=community_run_id,
            metrics=metrics,
        )

    return await _apply_session_change(session, context=context, change=_change)


async def _load_community_blacklist_status(
    *, session: Any, subreddit: str
) -> bool | None:
    return await load_community_blacklist_status(
        session=session,
        subreddit=subreddit,
    )


def _compensation_target_deps() -> CompensationTargetDeps:
    return CompensationTargetDeps(
        settings_factory=get_settings,
        ensure_dict=_ensure_dict,
        ensure_crawler_run_target=ensure_crawler_run_target,
        enqueue_target_outbox=enqueue_execute_target_outbox,
        compensation_queue=COMPENSATION_QUEUE,
        backfill_posts_queue=BACKFILL_POSTS_QUEUE,
    )


def _build_global_rate_limiter(*, settings: Any, plan_kind: str) -> Any | None:
    return build_global_rate_limiter(
        settings=settings,
        plan_kind=plan_kind,
        crawler_global_bucket_enabled=CRAWLER_GLOBAL_BUCKET_ENABLED,
    )


def _needs_community_lock(plan_kind: str) -> bool:
    return needs_community_lock(plan_kind, locked_plan_kinds=LOCKED_PLAN_KINDS)


async def _try_acquire_community_lock(
    *, session: Any, community_name: str
) -> bool:
    return await try_acquire_community_lock(
        session=session,
        community_name=community_name,
    )


async def _release_community_lock(*, session: Any, community_name: str) -> None:
    await release_community_lock(
        session=session,
        community_name=community_name,
    )


def _parse_iso_datetime(value: str | None) -> datetime | None:
    return parse_iso_datetime(value)


def _backfill_done_months() -> int:
    return backfill_done_months()


def _backfill_posts_min() -> int:
    return backfill_posts_min()


def _backfill_comments_min() -> int:
    return backfill_comments_min()


async def _count_posts_since(
    *, session: Any, subreddit: str, since: datetime
) -> int:
    return await count_posts_since(
        session=session,
        subreddit=subreddit,
        since=since,
    )


async def _count_comments_since(
    *, session: Any, subreddit: str, since: datetime
) -> int:
    return await count_comments_since(
        session=session,
        subreddit=subreddit,
        since=since,
    )


async def _load_backfill_floor(
    *, session: Any, subreddit: str
) -> datetime | None:
    return await load_backfill_floor(
        session=session,
        subreddit=subreddit,
    )


async def _finalize_backfill_status(
    *,
    session: Any,
    subreddit: str,
    plan: CrawlPlanContract,
    outcome: dict[str, object],
) -> None:
    await finalize_backfill_status(
        session=session,
        subreddit=subreddit,
        plan=plan,
        outcome=outcome,
        parse_iso_datetime_func=_parse_iso_datetime,
        backfill_done_months_func=_backfill_done_months,
        backfill_posts_min_func=_backfill_posts_min,
        backfill_comments_min_func=_backfill_comments_min,
        load_backfill_floor_func=_load_backfill_floor,
        count_posts_since_func=_count_posts_since,
        count_comments_since_func=_count_comments_since,
        update_backfill_status_func=update_backfill_status,
    )


def _trigger_deps() -> ExecuteTargetTriggerDeps:
    return ExecuteTargetTriggerDeps(
        send_task=celery_app.send_task,
        env_get=os.getenv,
        probe_queue="probe_queue",
        backfill_posts_queue=BACKFILL_POSTS_QUEUE,
    )


def _should_auto_trigger_evaluator(
    *, plan: Any, outcome: dict[str, object]
) -> bool:
    return should_auto_trigger_evaluator(plan=plan, outcome=outcome, deps=_trigger_deps())


def _execute_target_workflow_deps() -> ExecuteTargetWorkflowDeps:
    return build_execute_target_workflow_deps(
        session_factory=SessionFactory,
        settings_factory=get_settings,
        reddit_client_cls=RedditAPIClient,
        execute_crawl_plan_func=execute_crawl_plan,
        parse_uuid_func=_parse_uuid,
        ensure_dict_func=_ensure_dict,
        audit_missing_target_func=_audit_missing_target,
        rollback_session_quietly_func=_rollback_session_quietly,
        commit_session_func=_commit_session,
        apply_session_change_func=_apply_session_change,
        set_target_failed_func=_set_target_failed,
        set_target_partial_func=_set_target_partial,
        set_target_completed_func=_set_target_completed,
        load_community_blacklist_status_func=_load_community_blacklist_status,
        needs_community_lock_func=_needs_community_lock,
        try_acquire_community_lock_func=_try_acquire_community_lock,
        release_community_lock_func=_release_community_lock,
        build_global_rate_limiter_func=_build_global_rate_limiter,
        finalize_backfill_status_func=_finalize_backfill_status,
        build_compensation_target_deps_func=_compensation_target_deps,
        enqueue_compensation_target_func=enqueue_compensation_target,
        build_trigger_deps_func=_trigger_deps,
        auto_trigger_evaluator_best_effort_func=auto_trigger_evaluator_best_effort,
        maybe_trigger_candidate_vetting_check_func=maybe_trigger_candidate_vetting_check,
        mark_crawl_attempt_func=mark_crawl_attempt,
        mark_backfill_running_func=mark_backfill_running,
        mark_backfill_status_only_func=mark_backfill_status_only,
        patrol_target_time_budget_seconds=PATROL_TARGET_TIME_BUDGET_SECONDS,
    )


async def _execute_target_impl(*, target_id: str) -> dict[str, object]:
    return await run_execute_target_task(
        target_id=target_id,
        build_execute_target_workflow_deps_func=_execute_target_workflow_deps,
        execute_target_workflow_func=execute_target_workflow,
    )


@celery_app.task(name="tasks.crawler.execute_target")  # type: ignore[misc]
def execute_target(*, target_id: str) -> dict[str, object]:
    logger.info("Execute target: %s", target_id)
    return run_coro(_execute_target_impl(target_id=target_id))


__all__ = ["execute_target"]
