from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
import uuid
from typing import Any
from datetime import datetime, timedelta, timezone

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
from app.services.crawl.plan_contract import CrawlPlanContract, compute_idempotency_key
from app.services.crawl.crawler_run_targets_service import (
    complete_crawler_run_target,
    ensure_crawler_run_target,
    fail_crawler_run_target,
    partial_crawler_run_target,
)
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditGlobalRateLimitExceeded
from app.utils.asyncio_runner import run as run_coro
from app.utils.subreddit import subreddit_key

logger = get_task_logger(__name__)

PATROL_TARGET_TIME_BUDGET_SECONDS = float(
    os.getenv("PATROL_TARGET_TIME_BUDGET_SECONDS", "120")
)
COMPENSATION_QUEUE = os.getenv("CRAWLER_COMPENSATION_QUEUE", "compensation_queue")
BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")
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
    try:
        return str(uuid.UUID(str(value)))
    except Exception as exc:
        raise ValueError("target_id must be a UUID string") from exc


def _ensure_dict(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
    return {}


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


def _compute_compensation_idempotency_key(
    *,
    base_idempotency_key: str,
    reason: str,
    cursor_after: str | None,
    missing_set_hash: str | None,
    length: int = 16,
) -> str:
    raw = json.dumps(
        {
            "base": base_idempotency_key,
            "kind": "compensation",
            "reason": reason,
            "cursor_after": cursor_after,
            "missing_set_hash": missing_set_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[: max(8, min(length, len(digest)))]


def _compute_compensation_idempotency_key_human(
    *, plan: CrawlPlanContract, reason: str, cursor_after: str | None
) -> str:
    suffix = f"|after={cursor_after}" if cursor_after else ""
    return f"{plan.target_type}:{plan.target_value}|{plan.plan_kind}|compensate|{reason}{suffix}"


async def _compute_compensation_delay_seconds(*, session: Any, crawl_run_id: str) -> int:
    settings = get_settings()
    if not settings.compensation_delay_enabled:
        return 0

    base_delay = max(0, int(settings.compensation_base_delay_seconds))
    max_delay = max(0, int(settings.compensation_max_delay_seconds))
    jitter = max(0, int(settings.compensation_jitter_seconds))
    batch_size = max(1, int(settings.compensation_batch_size))
    if base_delay <= 0 and jitter <= 0:
        return 0

    try:
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                  AND (
                    config @> '{"meta": {"is_compensation": true}}'::jsonb
                    OR config @> '{"meta": {"is_compensation": "true"}}'::jsonb
                  )
                """
            ),
            {"rid": crawl_run_id},
        )
        count = int(result.scalar() or 0)
        if count <= 0:
            rows = await session.execute(
                text(
                    """
                    SELECT config
                    FROM crawler_run_targets
                    WHERE crawl_run_id = CAST(:rid AS uuid)
                      AND config::text ILIKE '%is_compensation%'
                    """
                ),
                {"rid": crawl_run_id},
            )
            count = 0
            for row in rows.all():
                cfg = _ensure_dict(row[0])
                meta = _ensure_dict(cfg.get("meta"))
                flag = meta.get("is_compensation")
                if isinstance(flag, str):
                    flag = flag.strip().lower() == "true"
                if flag is True:
                    count += 1
    except Exception:
        return 0

    if count <= 0:
        return 0

    batch_index = max(0, (count - 1) // batch_size)
    delay = base_delay * batch_index
    if jitter > 0:
        delay += random.randint(0, jitter)
    if max_delay > 0:
        delay = min(delay, max_delay)
    return delay


async def _enqueue_compensation_target(
    *,
    session: Any,
    crawl_run_id: str,
    subreddit: str,
    original_target_id: str,
    plan: CrawlPlanContract,
    base_idempotency_key: str,
    reason: str,
    cursor_after: str | None = None,
    missing_set_hash: str | None = None,
    countdown_seconds: int | None = None,
) -> str | None:
    meta = dict(plan.meta or {})
    meta.update(
        {
            "is_compensation": True,
            "retry_of_target_id": original_target_id,
            "compensation_reason": reason,
        }
    )
    if cursor_after:
        meta["cursor_after"] = cursor_after
    if missing_set_hash:
        meta["missing_set_hash"] = missing_set_hash

    compensation_plan = CrawlPlanContract(
        plan_kind=plan.plan_kind,
        target_type=plan.target_type,
        target_value=plan.target_value,
        reason=plan.reason,
        window=plan.window,
        limits=plan.limits,
        meta=meta,
    )

    comp_key = _compute_compensation_idempotency_key(
        base_idempotency_key=base_idempotency_key,
        reason=reason,
        cursor_after=cursor_after,
        missing_set_hash=missing_set_hash,
    )
    comp_key_human = _compute_compensation_idempotency_key_human(
        plan=plan, reason=reason, cursor_after=cursor_after
    )
    comp_target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{comp_key}")
    )

    comp_dedupe_key = f"compensation:{crawl_run_id}:{comp_key}"
    was_inserted = await ensure_crawler_run_target(
        session,
        community_run_id=comp_target_id,
        crawl_run_id=crawl_run_id,
        subreddit=subreddit,
        status="queued",
        plan_kind=compensation_plan.plan_kind,
        idempotency_key=comp_key,
        idempotency_key_human=comp_key_human,
        dedupe_key=comp_dedupe_key,
        config=compensation_plan.model_dump(mode="json"),
    )
    if not was_inserted:
        return None

    computed_delay = await _compute_compensation_delay_seconds(
        session=session,
        crawl_run_id=crawl_run_id,
    )
    requested_delay = int(countdown_seconds or 0)
    final_delay = max(0, max(requested_delay, computed_delay))
    queue = COMPENSATION_QUEUE
    if compensation_plan.plan_kind == "backfill_posts":
        queue = BACKFILL_POSTS_QUEUE
    await enqueue_execute_target_outbox(
        session,
        target_id=comp_target_id,
        queue=queue,
        countdown=final_delay if final_delay > 0 else None,
    )
    return comp_target_id


def _build_global_rate_limiter(*, settings: Any, plan_kind: str) -> Any | None:
    if not CRAWLER_GLOBAL_BUCKET_ENABLED:
        return None

    try:
        import redis.asyncio as redis  # type: ignore
    except Exception:
        return None

    try:
        from app.services.infrastructure.global_rate_limiter import GlobalRateLimiter
    except Exception:
        return None

    try:
        share_raw = os.getenv("CRAWLER_PATROL_BUCKET_SHARE", "0.4")
        patrol_share = float(share_raw)
    except Exception:
        patrol_share = 0.4
    patrol_share = max(0.05, min(0.95, patrol_share))

    total_limit = max(1, int(getattr(settings, "reddit_rate_limit", 1) or 1))
    window_seconds = int(
        float(getattr(settings, "reddit_rate_limit_window_seconds", 60.0) or 60.0)
    )
    window_seconds = max(1, window_seconds)

    patrol_limit = max(1, int(round(total_limit * patrol_share)))
    bulk_limit = max(1, total_limit - patrol_limit)
    is_patrol = str(plan_kind) == "patrol"
    bucket_name = "patrol" if is_patrol else "bulk"
    bucket_limit = patrol_limit if is_patrol else bulk_limit

    try:
        client_id = str(getattr(settings, "reddit_client_id", "") or "default")
        rclient = redis.Redis.from_url(getattr(settings, "reddit_cache_redis_url"))
        return GlobalRateLimiter(
            rclient,
            limit=bucket_limit,
            window_seconds=window_seconds,
            namespace=f"reddit_api:qpm:{bucket_name}",
            client_id=client_id,
        )
    except Exception:
        return None


def _needs_community_lock(plan_kind: str) -> bool:
    return str(plan_kind) in LOCKED_PLAN_KINDS


async def _try_acquire_community_lock(
    *, session: Any, community_name: str
) -> bool:
    lock_key = subreddit_key(community_name)
    result = await session.execute(
        text("SELECT pg_try_advisory_lock(hashtext(:key))"),
        {"key": lock_key},
    )
    return bool(result.scalar() or False)


async def _release_community_lock(*, session: Any, community_name: str) -> None:
    lock_key = subreddit_key(community_name)
    await session.execute(
        text("SELECT pg_advisory_unlock(hashtext(:key))"),
        {"key": lock_key},
    )


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _backfill_done_months() -> int:
    return max(1, int(os.getenv("BACKFILL_DONE_MONTHS", "12")))


def _backfill_posts_min() -> int:
    return max(1, int(os.getenv("BACKFILL_DONE_POSTS_MIN", "1000")))


def _backfill_comments_min() -> int:
    return max(1, int(os.getenv("BACKFILL_DONE_COMMENTS_MIN", "20000")))


async def _count_posts_since(
    *, session: Any, subreddit: str, since: datetime
) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM posts_raw
            WHERE subreddit = :subreddit
              AND created_at >= :since
            """
        ),
        {"subreddit": subreddit_key(subreddit), "since": since},
    )
    return int(result.scalar() or 0)


async def _count_comments_since(
    *, session: Any, subreddit: str, since: datetime
) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM comments
            WHERE subreddit = :subreddit
              AND created_utc >= :since
            """
        ),
        {"subreddit": subreddit_key(subreddit), "since": since},
    )
    return int(result.scalar() or 0)


async def _load_backfill_floor(
    *, session: Any, subreddit: str
) -> datetime | None:
    result = await session.execute(
        text(
            """
            SELECT backfill_floor
            FROM community_cache
            WHERE community_name = :name
            """
        ),
        {"name": subreddit_key(subreddit)},
    )
    floor = result.scalar_one_or_none()
    if floor is not None and getattr(floor, "tzinfo", None) is None:
        floor = floor.replace(tzinfo=timezone.utc)
    return floor


async def _finalize_backfill_status(
    *,
    session: Any,
    subreddit: str,
    plan: CrawlPlanContract,
    outcome: dict[str, object],
) -> None:
    now = datetime.now(timezone.utc)
    window_since = plan.window.since if plan.window is not None else None
    min_seen = _parse_iso_datetime(str(outcome.get("min_seen_created_at") or ""))
    cursor_after = str(outcome.get("cursor_after") or "") or None
    reason = str(outcome.get("reason") or "")
    total_fetched = int(outcome.get("total_fetched") or 0)
    posts_limit = int(plan.limits.posts_limit or 0)
    hit_posts_limit = bool(outcome.get("hit_posts_limit"))
    if posts_limit > 0 and total_fetched >= posts_limit:
        hit_posts_limit = True

    backfill_floor = await _load_backfill_floor(session=session, subreddit=subreddit)
    coverage_months = (
        max(0, (now - backfill_floor).days // 30) if backfill_floor else 0
    )

    since_window = now - timedelta(days=_backfill_done_months() * 30)
    sample_posts = await _count_posts_since(
        session=session, subreddit=subreddit, since=since_window
    )
    sample_comments = await _count_comments_since(
        session=session, subreddit=subreddit, since=since_window
    )

    backfill_capped = False
    if reason == "cursor_remaining" or hit_posts_limit:
        backfill_capped = True
    elif cursor_after:
        backfill_capped = False
    elif min_seen is not None and window_since is not None and min_seen > window_since:
        backfill_capped = True

    status = "NEEDS"
    done_floor = now - timedelta(days=_backfill_done_months() * 30)
    if backfill_floor is not None and backfill_floor <= done_floor:
        status = "DONE_12M"
    elif (
        backfill_capped
        and sample_posts >= _backfill_posts_min()
        and sample_comments >= _backfill_comments_min()
    ):
        status = "DONE_CAPPED"
    elif backfill_capped:
        status = "ERROR"

    await update_backfill_status(
        subreddit_key(subreddit),
        status=status,
        coverage_months=int(coverage_months),
        sample_posts=sample_posts,
        sample_comments=sample_comments,
        backfill_capped=backfill_capped,
        cursor_after=cursor_after,
        cursor_created_at=min_seen,
        session=session,
    )


def _should_auto_trigger_evaluator(*, plan: CrawlPlanContract, outcome: dict[str, object]) -> bool:
    if str(plan.plan_kind) != "probe":
        return False
    if os.getenv("PROBE_AUTO_EVALUATE_ENABLED", "1") != "1":
        return False
    try:
        upserted = int(outcome.get("discovered_communities_upserted") or 0)
    except Exception:
        upserted = 0
    return upserted > 0


def _auto_trigger_evaluator_best_effort(*, plan: CrawlPlanContract, outcome: dict[str, object]) -> None:
    if not _should_auto_trigger_evaluator(plan=plan, outcome=outcome):
        return
    try:
        celery_app.send_task("tasks.discovery.run_community_evaluation", queue="probe_queue")
    except Exception:
        # best-effort only; never block crawler execution
        return


def _maybe_trigger_candidate_vetting_check(*, plan: CrawlPlanContract) -> None:
    # candidate_vetting 回填完成后，需要聚合检查是否“整套切片都跑完”，再触发单社区评估
    if str(plan.plan_kind) != "backfill_posts":
        return
    if str(plan.reason or "") != "candidate_vetting":
        return
    try:
        celery_app.send_task(
            "tasks.discovery.check_candidate_vetting",
            kwargs={"community": str(plan.target_value)},
            queue=BACKFILL_POSTS_QUEUE,
        )
    except Exception:
        return


async def _execute_target_impl(*, target_id: str) -> dict[str, object]:
    """
    统一执行入口（Key 拍板版）：
    - 执行维度 = crawler_run_targets.id（这里叫 target_id）
    - 计划合同 = crawler_run_targets.config（JSONB）
    """
    settings = get_settings()
    normalized_id = _parse_uuid(target_id)

    async with SessionFactory() as session:
        # 绑定连接，确保 advisory lock 在执行期有效，但不要启用 AUTOCOMMIT（会导致 SAVEPOINT 失效）
        await session.connection()

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
                {"id": normalized_id},
            )
            record = row.mappings().first()
            if record is not None:
                break
            if attempt < 2:
                await asyncio.sleep(0.3)
        if record is None:
            try:
                await _audit_missing_target(
                    session=session, target_id=normalized_id, attempts=3
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
            return {
                "status": "failed",
                "reason": "target_missing",
                "target_id": normalized_id,
            }

        crawl_run_id = str(record["crawl_run_id"])
        subreddit = str(record["subreddit"])
        status = str(record["status"] or "")
        config = _ensure_dict(record["config"])
        existing_metrics = _ensure_dict(record["metrics"])
        base_idempotency_key = str(record.get("idempotency_key") or "")

        # 幂等护栏：已经完成的 target 不重复执行（避免重复抓取/重复写库）
        if status in {"completed", "partial"}:
            return {
                "status": "skipped",
                "reason": f"already_{status}",
                "crawl_run_id": crawl_run_id,
                "target_id": normalized_id,
                "community_run_id": normalized_id,
                "subreddit": subreddit,
                "metrics": existing_metrics,
            }

        # 幂等护栏：只允许 queued 进入执行，其他状态直接跳过
        if status != "queued":
            return {
                "status": "skipped",
                "reason": f"status_{status or 'unknown'}",
                "crawl_run_id": crawl_run_id,
                "target_id": normalized_id,
                "community_run_id": normalized_id,
                "subreddit": subreddit,
                "metrics": existing_metrics,
            }

        # 仅允许 queued -> running（原子更新，避免重复消费）
        updated = await session.execute(
            text(
                """
                UPDATE crawler_run_targets
                SET status = 'running'
                WHERE id = CAST(:id AS uuid)
                  AND status = 'queued'
                """
            ),
            {"id": normalized_id},
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
                {"id": normalized_id},
            )
            latest_status = str(latest.scalar_one_or_none() or "")
            return {
                "status": "skipped",
                "reason": f"status_{latest_status or 'unknown'}",
                "crawl_run_id": crawl_run_id,
                "target_id": normalized_id,
                "community_run_id": normalized_id,
                "subreddit": subreddit,
                "metrics": existing_metrics,
            }
        try:
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            return {
                "status": "failed",
                "reason": "claim_commit_failed",
                "crawl_run_id": crawl_run_id,
                "target_id": normalized_id,
                "community_run_id": normalized_id,
                "subreddit": subreddit,
            }

        # Safety: never execute targets for communities that are blacklisted in the pool.
        # This prevents “pollution regrowth” when old outbox events/targets are still queued.
        try:
            blocked = await session.scalar(
                text(
                    """
                    SELECT is_blacklisted
                    FROM community_pool
                    WHERE name = :name
                    """
                ),
                {"name": subreddit},
            )
            if blocked is True:
                try:
                    await fail_crawler_run_target(
                        session,
                        community_run_id=normalized_id,
                        error_code="blocked_blacklisted",
                        error_message_short="community blacklisted in pool",
                    )
                    await session.commit()
                except Exception:
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                return {
                    "status": "failed",
                    "reason": "blocked_blacklisted",
                    "crawl_run_id": crawl_run_id,
                    "target_id": normalized_id,
                    "community_run_id": normalized_id,
                    "subreddit": subreddit,
                }
        except Exception:
            pass

        plan = CrawlPlanContract.model_validate(config)
        if plan.plan_kind == "backfill_posts" and int(getattr(plan, "version", 0) or 0) < 2:
            try:
                await partial_crawler_run_target(
                    session,
                    community_run_id=normalized_id,
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
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
            return {
                "status": "partial",
                "reason": "schema_mismatch",
                "crawl_run_id": crawl_run_id,
                "target_id": normalized_id,
                "community_run_id": normalized_id,
                "subreddit": subreddit,
                "plan_kind": plan.plan_kind,
            }
        if not base_idempotency_key:
            base_idempotency_key = compute_idempotency_key(plan)

        lock_acquired = False
        lock_target = None
        if _needs_community_lock(plan.plan_kind):
            lock_target = str(plan.target_value or subreddit)
            try:
                lock_acquired = await _try_acquire_community_lock(
                    session=session, community_name=lock_target
                )
            except Exception:
                lock_acquired = False
            if not lock_acquired:
                try:
                    await partial_crawler_run_target(
                        session,
                        community_run_id=normalized_id,
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
                    )
                    await session.commit()
                except Exception:
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                comp_target_id = None
                if plan.plan_kind != "probe":
                    try:
                        comp_target_id = await _enqueue_compensation_target(
                            session=session,
                            crawl_run_id=crawl_run_id,
                            subreddit=subreddit,
                            original_target_id=normalized_id,
                            plan=plan,
                            base_idempotency_key=base_idempotency_key,
                            reason="community_locked",
                            countdown_seconds=60,
                        )
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
                        comp_target_id = None
                return {
                    "status": "partial",
                    "reason": "community_locked",
                    "crawl_run_id": crawl_run_id,
                    "target_id": normalized_id,
                    "community_run_id": normalized_id,
                    "subreddit": subreddit,
                    "plan_kind": plan.plan_kind,
                    "compensation_target_id": comp_target_id,
                }
            # advisory lock 持有即可，避免事务跨网络请求
            try:
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

        if plan.plan_kind == "backfill_posts":
            try:
                await mark_backfill_running(plan.target_value, session=session)
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

        global_rate_limiter = _build_global_rate_limiter(
            settings=settings, plan_kind=str(plan.plan_kind)
        )

        try:
            async with RedditAPIClient(
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
                    coro = execute_crawl_plan(
                        plan=plan,
                        session=session,
                        reddit_client=reddit,
                        crawl_run_id=crawl_run_id,
                        community_run_id=normalized_id,
                    )
                    if (
                        plan.plan_kind == "patrol"
                        and PATROL_TARGET_TIME_BUDGET_SECONDS > 0
                    ):
                        outcome = await asyncio.wait_for(
                            coro, timeout=PATROL_TARGET_TIME_BUDGET_SECONDS
                        )
                    else:
                        outcome = await coro
                    duration = time.monotonic() - start
                    if isinstance(outcome, dict) and "duration_seconds" not in outcome:
                        outcome["duration_seconds"] = duration
                except asyncio.TimeoutError:
                    if plan.target_type == "subreddit":
                        try:
                            await mark_crawl_attempt(plan.target_value, session=session)
                        except Exception:
                            pass
                    if plan.plan_kind == "backfill_posts":
                        try:
                            await mark_backfill_status_only(
                                plan.target_value,
                                status="ERROR",
                                session=session,
                            )
                            await session.commit()
                        except Exception:
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                    try:
                        await partial_crawler_run_target(
                            session,
                            community_run_id=normalized_id,
                            error_code="timeout",
                            error_message_short="patrol target timed out",
                            metrics={
                                "error": "timeout",
                                "timeout_seconds": PATROL_TARGET_TIME_BUDGET_SECONDS,
                                "plan_kind": plan.plan_kind,
                                "metrics_schema_version": 2,
                                "stop_reason": "timeout",
                                "partial_reason": "timeout",
                                "api_calls_total": 0,
                                "pages_processed": 0,
                                "items_api_returned": 0,
                            },
                        )
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
                    comp_target_id = None
                    if plan.plan_kind != "probe":
                        try:
                            comp_target_id = await _enqueue_compensation_target(
                                session=session,
                                crawl_run_id=crawl_run_id,
                                subreddit=subreddit,
                                original_target_id=normalized_id,
                                plan=plan,
                                base_idempotency_key=base_idempotency_key,
                                reason="timeout",
                                countdown_seconds=60,
                            )
                            await session.commit()
                        except Exception:
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                            comp_target_id = None

                    return {
                        "status": "partial",
                        "reason": "timeout",
                        "crawl_run_id": crawl_run_id,
                        "target_id": normalized_id,
                        "community_run_id": normalized_id,
                        "subreddit": subreddit,
                        "plan_kind": plan.plan_kind,
                        "compensation_target_id": comp_target_id,
                    }
                except RedditGlobalRateLimitExceeded as exc:
                    if plan.target_type == "subreddit":
                        try:
                            await mark_crawl_attempt(plan.target_value, session=session)
                        except Exception:
                            pass
                    if plan.plan_kind == "backfill_posts":
                        try:
                            await mark_backfill_status_only(
                                plan.target_value,
                                status="ERROR",
                                session=session,
                            )
                            await session.commit()
                        except Exception:
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                    try:
                        await partial_crawler_run_target(
                            session,
                            community_run_id=normalized_id,
                            error_code="budget_exhausted",
                            error_message_short="global token bucket exhausted",
                            metrics={
                                "error": "budget_exhausted",
                                "wait_seconds": int(exc.wait_seconds),
                                "plan_kind": plan.plan_kind,
                            },
                        )
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
                    comp_target_id = None
                    if plan.plan_kind != "probe":
                        try:
                            comp_target_id = await _enqueue_compensation_target(
                                session=session,
                                crawl_run_id=crawl_run_id,
                                subreddit=subreddit,
                                original_target_id=normalized_id,
                                plan=plan,
                                base_idempotency_key=base_idempotency_key,
                                reason="budget_exhausted",
                                countdown_seconds=int(exc.wait_seconds),
                            )
                            await session.commit()
                        except Exception:
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                            comp_target_id = None
                    return {
                        "status": "partial",
                        "reason": "budget_exhausted",
                        "crawl_run_id": crawl_run_id,
                        "target_id": normalized_id,
                        "community_run_id": normalized_id,
                        "subreddit": subreddit,
                        "plan_kind": plan.plan_kind,
                        "compensation_target_id": comp_target_id,
                    }
                except Exception as exc:
                    if plan.target_type == "subreddit":
                        try:
                            await mark_crawl_attempt(plan.target_value, session=session)
                        except Exception:
                            pass
                    if plan.plan_kind == "backfill_posts":
                        try:
                            await mark_backfill_status_only(
                                plan.target_value,
                                status="ERROR",
                                session=session,
                            )
                            await session.commit()
                        except Exception:
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                    try:
                        await fail_crawler_run_target(
                            session,
                            community_run_id=normalized_id,
                            error_message_short=str(exc)[:400],
                        )
                        await session.commit()
                    except Exception:
                        pass
                    raise
        finally:
            if lock_acquired and lock_target:
                try:
                    await _release_community_lock(
                        session=session, community_name=lock_target
                    )
                except Exception:
                    pass

        if plan.plan_kind == "backfill_posts" and isinstance(outcome, dict):
            try:
                await _finalize_backfill_status(
                    session=session,
                    subreddit=plan.target_value,
                    plan=plan,
                    outcome=outcome,
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

        if isinstance(outcome, dict) and str(outcome.get("status") or "") == "partial":
            reason = str(outcome.get("reason") or "partial")
            cursor_after = str(outcome.get("cursor_after") or "") or None
            try:
                await partial_crawler_run_target(
                    session,
                    community_run_id=normalized_id,
                    error_code=reason,
                    error_message_short=str(outcome.get("error") or reason)[:400],
                    metrics=dict(outcome),
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

            # budget_cap=True 表示“额度回填”：窗口扫不干净也算正常收尾，不要自动补偿把额度越补越大
            if bool(plan.meta.get("budget_cap")) and reason == "cursor_remaining":
                _maybe_trigger_candidate_vetting_check(plan=plan)
                return {
                    "status": "partial",
                    "reason": reason,
                    "crawl_run_id": crawl_run_id,
                    "target_id": normalized_id,
                    "community_run_id": normalized_id,
                    "subreddit": subreddit,
                    "plan_kind": plan.plan_kind,
                    "compensation_target_id": None,
                }

            if plan.plan_kind == "probe":
                _auto_trigger_evaluator_best_effort(plan=plan, outcome=dict(outcome))
                return {
                    "status": "partial",
                    "reason": reason,
                    "crawl_run_id": crawl_run_id,
                    "target_id": normalized_id,
                    "community_run_id": normalized_id,
                    "subreddit": subreddit,
                    "plan_kind": plan.plan_kind,
                    "compensation_target_id": None,
                }

            try:
                comp_target_id = await _enqueue_compensation_target(
                    session=session,
                    crawl_run_id=crawl_run_id,
                    subreddit=subreddit,
                    original_target_id=normalized_id,
                    plan=plan,
                    base_idempotency_key=base_idempotency_key,
                    reason=reason,
                    cursor_after=cursor_after,
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
                comp_target_id = None

            return {
                "status": "partial",
                "reason": reason,
                "crawl_run_id": crawl_run_id,
                "target_id": normalized_id,
                "community_run_id": normalized_id,
                "subreddit": subreddit,
                "plan_kind": plan.plan_kind,
                "compensation_target_id": comp_target_id,
            }

        try:
            await complete_crawler_run_target(
                session,
                community_run_id=normalized_id,
                metrics=dict(outcome),
            )
            await session.commit()
        except Exception:
            pass

        result: dict[str, object] = dict(outcome)
        result.setdefault("crawl_run_id", crawl_run_id)
        result.setdefault("target_id", normalized_id)
        result.setdefault("community_run_id", normalized_id)
        result.setdefault("subreddit", subreddit)
        result.setdefault("plan_kind", plan.plan_kind)
        if isinstance(outcome, dict):
            _auto_trigger_evaluator_best_effort(plan=plan, outcome=dict(outcome))
        _maybe_trigger_candidate_vetting_check(plan=plan)
        return result


@celery_app.task(name="tasks.crawler.execute_target")  # type: ignore[misc]
def execute_target(*, target_id: str) -> dict[str, object]:
    logger.info("Execute target: %s", target_id)
    return run_coro(_execute_target_impl(target_id=target_id))


__all__ = ["execute_target"]
