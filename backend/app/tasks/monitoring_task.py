from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import redis
from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import select, text

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.models.community_cache import CommunityCache
from app.schemas.monitoring import CacheHealthResult
from app.services.community.community_pool_loader import CommunityPoolLoader
from app.services.infrastructure.cache_manager import CacheManager
from app.services.infrastructure.contract_health_workflow import (
    build_contract_health_result as _build_contract_health_result,
    finalize_contract_health_result as _finalize_contract_health_result,
)
from app.services.infrastructure.monitoring_support import (
    build_contract_health_thresholds as _build_contract_health_thresholds,
    build_monitoring_error_result as _build_monitoring_error_result,
    load_cache_seed_names as _load_cache_seed_names,
    load_entity_extraction_metrics as _load_entity_extraction_metrics,
    mark_payload_degraded as _mark_payload_degraded,
    run_cache_maintenance_tasks as _run_cache_maintenance_tasks,
    serialize_monitoring_result as _serialize_monitoring_result,
    utc_now as _utc_now,
    write_contract_health_audit_events as _write_contract_health_audit_events,
)
from app.services.infrastructure.monitoring_task_runtime import (
    build_monitoring_runtime_dependencies,
    calculate_monitor_cache_health as _calculate_cache_health_runtime,
    load_community_pool_size as _load_community_pool_size_runtime,
    run_collect_test_logs as _run_collect_test_logs,
    run_monitor_api_calls as _run_monitor_api_calls,
    run_monitor_cache_health as _run_monitor_cache_health,
    run_monitor_contract_health as _run_monitor_contract_health,
    run_monitor_e2e_tests as _run_monitor_e2e_tests,
    run_monitor_warmup_metrics as _run_monitor_warmup_metrics,
    run_update_performance_dashboard as _run_update_performance_dashboard,
)
from app.services.infrastructure.monitoring_task_support import (
    as_float as _as_float_support,
    as_int as _as_int_support,
    decode_int as _decode_int_support,
    get_metrics_redis as _get_metrics_redis_support,
    load_e2e_metrics as _load_e2e_metrics_support,
    load_route_call_metrics as _load_route_call_metrics_support,
    route_metrics_bucket as _route_metrics_bucket_support,
    send_alert as _send_alert_support,
    update_dashboard as _update_dashboard_support,
)
from app.utils.asyncio_runner import run as run_coro

logger = get_task_logger(__name__)
_LOGGER = logging.getLogger(__name__)

API_CALL_THRESHOLD = int(os.getenv("MONITOR_API_THRESHOLD", "55"))
CACHE_HIT_THRESHOLD = float(os.getenv("MONITOR_CACHE_HIT_THRESHOLD", "0.70"))
CRAWL_STALE_MINUTES = int(os.getenv("MONITOR_CRAWL_STALE_MINUTES", "90"))
METRICS_REDIS_URL = os.getenv("MONITOR_REDIS_URL")
TEST_LOG_PATH = Path(os.getenv("TEST_LOG_PATH", "tmp/test_runs/e2e.log"))
TEST_METRICS_PATH = Path(
    os.getenv("TEST_METRICS_PATH", "tmp/test_runs/e2e_metrics.json")
)
E2E_MAX_DURATION = float(os.getenv("E2E_MAX_DURATION_SECONDS", "300"))
E2E_MAX_FAILURE_RATE = float(os.getenv("E2E_MAX_FAILURE_RATE", "0.05"))
PERFORMANCE_DASHBOARD_KEY = os.getenv(
    "PERFORMANCE_DASHBOARD_KEY", "dashboard:performance"
)
ROUTE_METRICS_TOP_N = int(os.getenv("ROUTE_METRICS_TOP_N", "5"))
FACTS_AUDIT_BACKLOG_THRESHOLD = int(
    os.getenv("FACTS_AUDIT_BACKLOG_THRESHOLD", "5000")
)
FACTS_AUDIT_MAX_STALE_HOURS = int(
    os.getenv("FACTS_AUDIT_MAX_STALE_HOURS", "36")
)
TASK_STALL_THRESHOLD_MINUTES = int(
    os.getenv("TASK_STALL_THRESHOLD_MINUTES", "30")
)
TASK_STALL_MAX_BATCH = int(os.getenv("TASK_STALL_MAX_BATCH", "50"))
CONTRACT_HEALTH_WINDOW_HOURS = int(
    os.getenv("CONTRACT_HEALTH_WINDOW_HOURS", "24") or 24
)


def _as_float(value: object, *, default: float) -> float:
    return _as_float_support(value, default=default)


def _as_int(value: object, *, default: int) -> int:
    return _as_int_support(value, default=default)


def _get_metrics_redis(settings: Settings) -> redis.Redis:  # type: ignore[type-arg]
    return _get_metrics_redis_support(settings, metrics_redis_url=METRICS_REDIS_URL)


def _send_alert(level: str, message: str) -> None:
    _send_alert_support(
        task_logger=logger,
        std_logger=_LOGGER,
        level=level,
        message=message,
    )


def _load_e2e_metrics() -> dict[str, Any] | None:
    return _load_e2e_metrics_support(
        test_metrics_path=TEST_METRICS_PATH,
        std_logger=_LOGGER,
    )


def _update_dashboard(settings: Settings, values: dict[str, Any]) -> None:
    _update_dashboard_support(
        settings,
        values,
        get_metrics_redis=_get_metrics_redis,
        performance_dashboard_key=PERFORMANCE_DASHBOARD_KEY,
        utc_now=_utc_now,
    )


def _route_metrics_bucket() -> int:
    return _route_metrics_bucket_support(utc_now=_utc_now)


def _decode_int(value: Any) -> int:
    return _decode_int_support(value)


async def _calculate_monitor_cache_health(
    *,
    cache_manager: CacheManager,
) -> CacheHealthResult:
    return await _calculate_cache_health_runtime(
        cache_manager=cache_manager,
        cache_hit_threshold=CACHE_HIT_THRESHOLD,
        utc_now=_utc_now,
        send_alert=_send_alert,
        logger=_LOGGER,
        load_cache_seed_names=_load_cache_seed_names,
        load_entity_extraction_metrics=_load_entity_extraction_metrics,
        mark_payload_degraded=_mark_payload_degraded,
        run_cache_maintenance_tasks=_run_cache_maintenance_tasks,
    )


def _load_route_call_metrics(
    client: redis.Redis,  # type: ignore[type-arg]
    *,
    bucket: int,
    top_n: int = ROUTE_METRICS_TOP_N,
) -> tuple[int, int, list[dict[str, Any]]]:
    return _load_route_call_metrics_support(
        client,
        bucket=bucket,
        top_n=top_n,
    )


async def _load_community_pool_size() -> int:
    from app.db.session import SessionFactory

    return await _load_community_pool_size_runtime(
        session_factory=SessionFactory,
        community_pool_loader_cls=CommunityPoolLoader,
    )


def _runtime_deps() -> Any:
    return build_monitoring_runtime_dependencies(
        get_metrics_redis=_get_metrics_redis,
        send_alert=_send_alert,
        load_e2e_metrics=_load_e2e_metrics,
        update_dashboard=_update_dashboard,
        route_metrics_bucket=_route_metrics_bucket,
        load_route_call_metrics=_load_route_call_metrics,
        cache_manager_factory=CacheManager,
        run_coro=run_coro,
        calculate_cache_health=_calculate_monitor_cache_health,
        build_error_result=_build_monitoring_error_result,
        serialize_result=_serialize_monitoring_result,
        as_int=_as_int,
        as_float=_as_float,
        utc_now=_utc_now,
        build_contract_health_thresholds=_build_contract_health_thresholds,
        build_contract_health_result=_build_contract_health_result,
        finalize_contract_health_result=_finalize_contract_health_result,
        write_contract_health_audit_events=_write_contract_health_audit_events,
        load_community_pool_size=_load_community_pool_size,
    )


@celery_app.task(name="tasks.monitoring.monitor_api_calls")  # type: ignore[misc]
def monitor_api_calls() -> dict[str, Any]:
    settings = get_settings()
    deps = _runtime_deps()
    return _run_monitor_api_calls(
        settings=settings,
        api_call_threshold=API_CALL_THRESHOLD,
        get_metrics_redis=deps.get_metrics_redis,
        send_alert=deps.send_alert,
    )


@celery_app.task(name="tasks.monitoring.monitor_cache_health")  # type: ignore[misc]
def monitor_cache_health() -> dict[str, Any]:
    settings = get_settings()
    deps = _runtime_deps()
    return _run_monitor_cache_health(
        settings=settings,
        cache_manager_factory=deps.cache_manager_factory,
        run_coro=deps.run_coro,
        calculate_cache_health=deps.calculate_cache_health,
        serialize_result=deps.serialize_result,
        build_error_result=deps.build_error_result,
        send_alert=deps.send_alert,
    )


@celery_app.task(name="tasks.monitoring.monitor_crawler_health")  # type: ignore[misc]
def monitor_crawler_health() -> dict[str, Any]:
    get_settings()

    async def _load() -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=CRAWL_STALE_MINUTES)
        from app.db.session import SessionFactory

        async with SessionFactory() as session:
            result = await session.execute(
                select(
                    CommunityCache.community_name, CommunityCache.last_crawled_at
                ).where(CommunityCache.last_crawled_at < cutoff)
            )
            rows = result.all()
            stale = [
                {
                    "community": row.community_name,
                    "last_crawled_at": row.last_crawled_at.isoformat()
                    if row.last_crawled_at
                    else None,
                }
                for row in rows
            ]
            if stale:
                _send_alert(
                    "warning",
                    f"{len(stale)} 个社区超过 {CRAWL_STALE_MINUTES} 分钟未刷新",
                )
            return {
                "stale_communities": stale,
                "threshold_minutes": CRAWL_STALE_MINUTES,
            }

    return run_coro(_load())


@celery_app.task(name="tasks.monitoring.monitor_facts_audit_cleanup")  # type: ignore[misc]
def monitor_facts_audit_cleanup() -> dict[str, Any]:
    settings = get_settings()
    enabled = os.getenv("ENABLE_FACTS_AUDIT_CLEANUP", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    async def _load() -> dict[str, Any]:
        from app.db.session import SessionFactory

        now = _utc_now()
        expired_snapshots = 0
        expired_run_logs = 0
        last_cleanup_at: datetime | None = None
        last_cleanup_affected = 0
        last_cleanup_deleted_snapshots = 0
        last_cleanup_deleted_run_logs = 0

        async with SessionFactory() as db:
            has_snapshots = (
                await db.execute(text("SELECT to_regclass('public.facts_snapshots')"))
            ).scalar_one_or_none() is not None
            has_run_logs = (
                await db.execute(text("SELECT to_regclass('public.facts_run_logs')"))
            ).scalar_one_or_none() is not None
            has_audit = (
                await db.execute(text("SELECT to_regclass('public.maintenance_audit')"))
            ).scalar_one_or_none() is not None

            if has_snapshots:
                row = await db.execute(
                    text(
                        """
                        SELECT COUNT(*)::bigint
                        FROM facts_snapshots
                        WHERE expires_at IS NOT NULL AND expires_at < :now
                        """
                    ),
                    {"now": now},
                )
                expired_snapshots = int(row.scalar() or 0)

            if has_run_logs:
                row = await db.execute(
                    text(
                        """
                        SELECT COUNT(*)::bigint
                        FROM facts_run_logs
                        WHERE expires_at IS NOT NULL AND expires_at < :now
                        """
                    ),
                    {"now": now},
                )
                expired_run_logs = int(row.scalar() or 0)

            if has_audit:
                row = await db.execute(
                    text(
                        """
                        SELECT started_at, affected_rows, extra
                        FROM maintenance_audit
                        WHERE task_name = 'cleanup_expired_facts_audit'
                        ORDER BY started_at DESC
                        LIMIT 1
                        """
                    )
                )
                record = row.mappings().first()
                if record:
                    last_cleanup_at = record.get("started_at")
                    last_cleanup_affected = int(record.get("affected_rows") or 0)
                    extra = record.get("extra") or {}
                    if isinstance(extra, dict):
                        last_cleanup_deleted_snapshots = int(
                            extra.get("deleted_snapshots") or 0
                        )
                        last_cleanup_deleted_run_logs = int(
                            extra.get("deleted_run_logs") or 0
                        )

        backlog_total = expired_snapshots + expired_run_logs
        last_cleanup_age_hours: float | None = None
        if last_cleanup_at:
            last_cleanup_age_hours = (now - last_cleanup_at).total_seconds() / 3600.0

        status = "ok"
        if not enabled:
            status = "disabled"
        elif last_cleanup_at is None:
            status = "missing"
        elif (
            last_cleanup_age_hours is not None
            and last_cleanup_age_hours > FACTS_AUDIT_MAX_STALE_HOURS
        ):
            status = "stale"

        return {
            "status": status,
            "cleanup_enabled": enabled,
            "expired_snapshots": expired_snapshots,
            "expired_run_logs": expired_run_logs,
            "backlog_total": backlog_total,
            "last_cleanup_at": last_cleanup_at.isoformat() if last_cleanup_at else None,
            "last_cleanup_age_hours": last_cleanup_age_hours,
            "last_cleanup_affected_rows": last_cleanup_affected,
            "last_cleanup_deleted_snapshots": last_cleanup_deleted_snapshots,
            "last_cleanup_deleted_run_logs": last_cleanup_deleted_run_logs,
        }

    payload = run_coro(_load())
    _update_dashboard(settings, {"facts_audit_cleanup": payload})

    backlog_total = int(payload.get("backlog_total") or 0)
    status = str(payload.get("status") or "unknown")
    if status in {"missing", "stale"} and enabled:
        _send_alert(
            "warning",
            f"facts 审计清理异常: status={status} last_cleanup_at={payload.get('last_cleanup_at')}",
        )
    if backlog_total > FACTS_AUDIT_BACKLOG_THRESHOLD:
        _send_alert(
            "warning",
            f"facts 审计过期堆积: backlog={backlog_total} threshold={FACTS_AUDIT_BACKLOG_THRESHOLD}",
        )
    return payload


@celery_app.task(name="tasks.monitoring.monitor_e2e_tests")  # type: ignore[misc]
def monitor_e2e_tests() -> dict[str, Any]:
    settings = get_settings()
    result = _run_monitor_e2e_tests(
        settings=settings,
        load_e2e_metrics=_load_e2e_metrics,
        send_alert=_send_alert,
        update_dashboard=_update_dashboard,
        max_failure_rate=E2E_MAX_FAILURE_RATE,
        max_duration=E2E_MAX_DURATION,
    )
    if result.get("status") == "missing":
        _LOGGER.info("未找到端到端测试指标文件: %s", TEST_METRICS_PATH)
    return result


@celery_app.task(name="tasks.monitoring.collect_test_logs")  # type: ignore[misc]
def collect_test_logs(max_lines: int = 200) -> dict[str, Any]:
    settings = get_settings()
    return _run_collect_test_logs(
        settings=settings,
        test_log_path=TEST_LOG_PATH,
        max_lines=max_lines,
        get_metrics_redis=_get_metrics_redis,
        send_alert=_send_alert,
    )


@celery_app.task(name="tasks.monitoring.update_performance_dashboard")  # type: ignore[misc]
def update_performance_dashboard() -> dict[str, Any]:
    settings = get_settings()
    deps = _runtime_deps()
    return _run_update_performance_dashboard(
        settings=settings,
        load_e2e_metrics=deps.load_e2e_metrics,
        get_metrics_redis=deps.get_metrics_redis,
        route_metrics_bucket=deps.route_metrics_bucket,
        load_route_call_metrics=deps.load_route_call_metrics,
        update_dashboard=deps.update_dashboard,
        route_metrics_top_n=ROUTE_METRICS_TOP_N,
    )


@celery_app.task(name="tasks.monitoring.monitor_warmup_metrics")  # type: ignore[misc]
def monitor_warmup_metrics() -> dict[str, Any]:
    settings = get_settings()
    return _run_monitor_warmup_metrics(
        settings=settings,
        monitor_api_calls=monitor_api_calls,
        monitor_cache_health=monitor_cache_health,
        monitor_crawler_health=monitor_crawler_health,
        run_coro=run_coro,
        load_community_pool_size=_load_community_pool_size,
        update_dashboard=_update_dashboard,
        send_alert=_send_alert,
    )


@celery_app.task(name="tasks.monitoring.watchdog_stalled_tasks")  # type: ignore[misc]
def watchdog_stalled_tasks() -> dict[str, Any]:
    """
    Contract B: kill "fake dead" tasks.

    Human goal:
    - If a task stays in `processing` for too long (worker stalled / dependency down),
      mark it FAILED with a clear failure_category and audit record.
    """

    threshold_minutes = max(1, int(TASK_STALL_THRESHOLD_MINUTES))
    max_batch = max(1, int(TASK_STALL_MAX_BATCH))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=threshold_minutes)

    category = "worker_stalled"
    try:
        inspect = celery_app.control.inspect()
        ping = inspect.ping() if inspect is not None else None
        if not ping:
            category = "system_dependency_down"
    except Exception:  # pragma: no cover
        category = "system_dependency_down"

    async def _run() -> dict[str, Any]:
        from app.db.session import SessionFactory
        from app.models.task import Task, TaskStatus

        async with SessionFactory() as session:
            result = await session.execute(
                select(Task)
                .where(
                    Task.status == TaskStatus.PROCESSING,
                    Task.started_at.is_not(None),
                    Task.started_at < cutoff,
                )
                .order_by(Task.started_at.asc())
                .limit(max_batch)
            )
            stalled = list(result.scalars().all())

            task_ids: list[str] = []
            for task in stalled:
                task_ids.append(str(task.id))
                task.status = TaskStatus.FAILED
                task.failure_category = category
                task.error_message = (
                    f"{category}: task stuck in processing > {threshold_minutes} minutes"
                )
                task.dead_letter_at = now
                task.completed_at = None
                task.updated_at = now

            if task_ids:
                payload = {
                    "stalled_count": len(task_ids),
                    "task_ids": task_ids[:20],
                    "threshold_minutes": threshold_minutes,
                    "failure_category": category,
                }
                await session.execute(
                    text(
                        """
                        INSERT INTO data_audit_events (
                            event_type, target_type, target_id, reason, source_component, new_value
                        )
                        VALUES (
                            'monitor', 'tasks', 'watchdog_stalled_tasks', :reason, 'watchdog_stalled_tasks',
                            CAST(:payload AS JSONB)
                        )
                        """
                    ),
                    {"reason": category, "payload": json.dumps(payload, ensure_ascii=False)},
                )

            await session.commit()

        return {
            "status": "ok",
            "stalled_count": len(task_ids),
            "failure_category": category,
            "threshold_minutes": threshold_minutes,
        }

    return run_coro(_run())


@celery_app.task(name="tasks.monitoring.monitor_contract_health")  # type: ignore[misc]
def monitor_contract_health(hours: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    deps = _runtime_deps()
    return _run_monitor_contract_health(
        settings=settings,
        hours=hours,
        as_int=deps.as_int,
        as_float=deps.as_float,
        default_window_hours=CONTRACT_HEALTH_WINDOW_HOURS,
        utc_now=deps.utc_now,
        build_contract_health_thresholds=deps.build_contract_health_thresholds,
        run_coro=deps.run_coro,
        build_contract_health_result=deps.build_contract_health_result,
        finalize_contract_health_result=deps.finalize_contract_health_result,
        update_dashboard=deps.update_dashboard,
        send_alert=deps.send_alert,
        write_contract_health_audit_events=deps.write_contract_health_audit_events,
        build_error_result=deps.build_error_result,
        serialize_result=deps.serialize_result,
    )


__all__ = [
    "monitor_api_calls",
    "monitor_cache_health",
    "monitor_crawler_health",
    "monitor_contract_health",
    "monitor_e2e_tests",
    "collect_test_logs",
    "update_performance_dashboard",
    "monitor_warmup_metrics",
    "watchdog_stalled_tasks",
]
