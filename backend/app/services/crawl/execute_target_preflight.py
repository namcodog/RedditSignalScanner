from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.services.crawl.plan_contract import CrawlPlanContract, compute_idempotency_key


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ExecuteTargetPreflightContext:
    crawl_run_id: str
    subreddit: str
    existing_metrics: dict[str, Any]
    plan: CrawlPlanContract
    base_idempotency_key: str
    lock_acquired: bool
    lock_target: str | None


@dataclass(slots=True, frozen=True)
class ExecuteTargetPreflightInput:
    session: Any
    target_id: str


@dataclass(slots=True, frozen=True)
class ExecuteTargetPreflightDeps:
    ensure_dict: Callable[[object], dict[str, Any]]
    audit_missing_target: Callable[..., Awaitable[None]]
    apply_session_change: Callable[..., Awaitable[bool]]
    commit_session: Callable[..., Awaitable[bool]]
    rollback_session_quietly: Callable[..., Awaitable[None]]
    set_target_failed: Callable[..., Awaitable[bool]]
    set_target_partial: Callable[..., Awaitable[bool]]
    load_community_blacklist_status: Callable[..., Awaitable[bool | None]]
    needs_community_lock: Callable[[str], bool]
    try_acquire_community_lock: Callable[..., Awaitable[bool]]
    enqueue_compensation_target: Callable[..., Awaitable[str | None]]
    mark_backfill_running: Callable[..., Awaitable[None]]


@dataclass(slots=True, frozen=True)
class ExecuteTargetPreflightResult:
    context: ExecuteTargetPreflightContext | None = None
    early_payload: dict[str, object] | None = None


def _early(**payload: object) -> ExecuteTargetPreflightResult:
    return ExecuteTargetPreflightResult(early_payload=dict(payload))


async def prepare_execute_target_preflight(
    *,
    preflight_input: ExecuteTargetPreflightInput,
    deps: ExecuteTargetPreflightDeps,
) -> ExecuteTargetPreflightResult:
    session = preflight_input.session
    target_id = preflight_input.target_id

    exists = (
        await session.execute(text("SELECT to_regclass('public.crawler_run_targets')"))
    ).scalar_one_or_none()
    if not exists:
        raise RuntimeError("crawler_run_targets table is missing; cannot execute target")

    record = None
    for attempt in range(3):
        row = await session.execute(
            text(
                """
                SELECT id, crawl_run_id, subreddit, status, config, metrics,
                       idempotency_key
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        record = row.mappings().first()
        if record is not None:
            break
        if attempt < 2:
            await asyncio.sleep(0.3)

    if record is None:
        async def _audit_change() -> None:
            await deps.audit_missing_target(
                session=session,
                target_id=target_id,
                attempts=3,
            )

        await deps.apply_session_change(
            session,
            context="audit_missing_target",
            change=_audit_change,
        )
        return _early(status="failed", reason="target_missing", target_id=target_id)

    crawl_run_id = str(record.get("crawl_run_id") or "")
    subreddit = str(record.get("subreddit") or "")
    status = str(record.get("status") or "")
    config = deps.ensure_dict(record.get("config"))
    existing_metrics = deps.ensure_dict(record.get("metrics"))
    base_idempotency_key = str(record.get("idempotency_key") or "")

    if status in {"completed", "partial"}:
        return _early(
            status="skipped",
            reason=f"already_{status}",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            metrics=existing_metrics,
        )

    if status != "queued":
        return _early(
            status="skipped",
            reason=f"status_{status or 'unknown'}",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            metrics=existing_metrics,
        )

    updated = await session.execute(
        text(
            """
            UPDATE crawler_run_targets
            SET status = 'running'
            WHERE id = CAST(:id AS uuid)
              AND status = 'queued'
            """
        ),
        {"id": target_id},
    )
    if not bool(getattr(updated, "rowcount", 0) or 0):
        latest = await session.execute(
            text(
                """
                SELECT status
                FROM crawler_run_targets
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": target_id},
        )
        latest_status = str(latest.scalar_one_or_none() or "")
        return _early(
            status="skipped",
            reason=f"status_{latest_status or 'unknown'}",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            metrics=existing_metrics,
        )
    if not await deps.commit_session(session, context="claim_target"):
        return _early(
            status="failed",
            reason="claim_commit_failed",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
        )

    try:
        blocked = await deps.load_community_blacklist_status(
            session=session,
            subreddit=subreddit,
        )
        if blocked is True:
            await deps.set_target_failed(
                session,
                community_run_id=target_id,
                error_code="blocked_blacklisted",
                error_message_short="community blacklisted in pool",
                context="blocked_blacklisted",
            )
            return _early(
                status="failed",
                reason="blocked_blacklisted",
                crawl_run_id=crawl_run_id,
                target_id=target_id,
                community_run_id=target_id,
                subreddit=subreddit,
            )
    except Exception as exc:
        logger.warning(
            "Community blacklist guard failed for %s: %s",
            subreddit,
            exc,
            exc_info=exc,
        )
        await deps.rollback_session_quietly(session, context="blacklist_guard_read")
        await deps.set_target_failed(
            session,
            community_run_id=target_id,
            error_code="blacklist_check_failed",
            error_message_short="community blacklist check failed",
            context="blacklist_check_failed",
        )
        return _early(
            status="failed",
            reason="blacklist_check_failed",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
        )

    plan = CrawlPlanContract.model_validate(config)
    if plan.plan_kind == "backfill_posts" and int(getattr(plan, "version", 0) or 0) < 2:
        await deps.set_target_partial(
            session,
            community_run_id=target_id,
            error_code="schema_mismatch",
            error_message_short="backfill plan schema_version too old",
            metrics={
                "error": "schema_mismatch",
                "plan_kind": plan.plan_kind,
                "plan_version": int(getattr(plan, "version", 0) or 0),
                "metrics_schema_version_expected": 2,
                "metrics_schema_version": 2,
                "stop_reason": "schema_mismatch",
                "partial_reason": "schema_mismatch",
                "api_calls_total": 0,
                "pages_processed": 0,
                "items_api_returned": 0,
            },
            context="schema_mismatch",
        )
        return _early(
            status="partial",
            reason="schema_mismatch",
            crawl_run_id=crawl_run_id,
            target_id=target_id,
            community_run_id=target_id,
            subreddit=subreddit,
            plan_kind=plan.plan_kind,
        )

    if not base_idempotency_key:
        base_idempotency_key = compute_idempotency_key(plan)

    lock_acquired = False
    lock_target: str | None = None
    if deps.needs_community_lock(plan.plan_kind):
        lock_target = str(plan.target_value or subreddit)
        try:
            lock_acquired = await deps.try_acquire_community_lock(
                session=session,
                community_name=lock_target,
            )
        except Exception:
            lock_acquired = False
        if not lock_acquired:
            await deps.set_target_partial(
                session,
                community_run_id=target_id,
                error_code="community_locked",
                error_message_short="community lock busy",
                metrics={
                    "error": "community_locked",
                    "plan_kind": plan.plan_kind,
                    "lock_skipped_count": 1,
                    "lock_target": lock_target,
                    "metrics_schema_version": 2,
                    "stop_reason": "community_locked",
                    "partial_reason": "community_locked",
                    "api_calls_total": 0,
                    "pages_processed": 0,
                    "items_api_returned": 0,
                },
                context="community_locked",
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
                        base_idempotency_key=base_idempotency_key,
                        reason="community_locked",
                        countdown_seconds=60,
                    )
                    await deps.commit_session(
                        session,
                        context="community_locked_compensation",
                    )
                except Exception:
                    await deps.rollback_session_quietly(
                        session,
                        context="community_locked_compensation",
                    )
                    comp_target_id = None
            return _early(
                status="partial",
                reason="community_locked",
                crawl_run_id=crawl_run_id,
                target_id=target_id,
                community_run_id=target_id,
                subreddit=subreddit,
                plan_kind=plan.plan_kind,
                compensation_target_id=comp_target_id,
            )
        await deps.commit_session(session, context="community_lock_hold")

    if plan.plan_kind == "backfill_posts":
        try:
            await deps.mark_backfill_running(plan.target_value, session=session)
            await deps.commit_session(session, context="mark_backfill_running")
        except Exception as exc:
            logger.warning(
                "Failed to mark backfill running for %s: %s",
                plan.target_value,
                exc,
                exc_info=exc,
            )
            await deps.rollback_session_quietly(session, context="mark_backfill_running")

    return ExecuteTargetPreflightResult(
        context=ExecuteTargetPreflightContext(
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            existing_metrics=existing_metrics,
            plan=plan,
            base_idempotency_key=base_idempotency_key,
            lock_acquired=lock_acquired,
            lock_target=lock_target,
        )
    )


__all__ = [
    "ExecuteTargetPreflightContext",
    "ExecuteTargetPreflightDeps",
    "ExecuteTargetPreflightInput",
    "ExecuteTargetPreflightResult",
    "prepare_execute_target_preflight",
]
