from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, cast

import redis
from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import select, text

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.middleware.route_metrics import DEFAULT_ROUTE_METRICS_KEY_PREFIX
from app.models.community_cache import CommunityCache
from app.services.cache_manager import CacheManager
from app.services.community_pool_loader import CommunityPoolLoader
from app.services.ops.contract_health import (
    ContractHealthAlert,
    ContractHealthAlertThresholds,
    ContractHealthRow,
    compute_contract_health,
    evaluate_contract_health_alerts,
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
FACTS_AUDIT_BACKLOG_THRESHOLD = int(os.getenv("FACTS_AUDIT_BACKLOG_THRESHOLD", "5000"))
FACTS_AUDIT_MAX_STALE_HOURS = int(os.getenv("FACTS_AUDIT_MAX_STALE_HOURS", "36"))
TASK_STALL_THRESHOLD_MINUTES = int(os.getenv("TASK_STALL_THRESHOLD_MINUTES", "30"))
TASK_STALL_MAX_BATCH = int(os.getenv("TASK_STALL_MAX_BATCH", "50"))
CONTRACT_HEALTH_WINDOW_HOURS = int(os.getenv("CONTRACT_HEALTH_WINDOW_HOURS", "24") or 24)


def _as_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _as_int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _get_metrics_redis(settings: Settings) -> redis.Redis:  # type: ignore[type-arg]
    target_url = METRICS_REDIS_URL or settings.reddit_cache_redis_url
    return redis.Redis.from_url(target_url)


def _send_alert(level: str, message: str) -> None:
    formatted = f"[{level.upper()}] {message}"
    logger.warning(formatted)
    _LOGGER.warning(formatted)


def _load_e2e_metrics() -> Optional[Dict[str, Any]]:
    if not TEST_METRICS_PATH.exists():
        return None
    try:
        payload = json.loads(TEST_METRICS_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        return payload
    except json.JSONDecodeError:
        _LOGGER.warning("无法解析测试指标文件: %s", TEST_METRICS_PATH)
        return None


def _update_dashboard(settings: Settings, values: Dict[str, Any]) -> None:
    client = _get_metrics_redis(settings)
    enriched: dict[str, str] = {
        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        for k, v in values.items()
    }
    client.hset(
        PERFORMANCE_DASHBOARD_KEY,
        mapping=cast(Mapping[str | bytes, bytes | float | int | str], enriched),
    )
    client.hset(
        PERFORMANCE_DASHBOARD_KEY, "updated_at", datetime.now(timezone.utc).isoformat()
    )


def _route_metrics_bucket() -> int:
    return int(datetime.now(timezone.utc).timestamp() // 60)


def _decode_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _load_route_call_metrics(
    client: redis.Redis,  # type: ignore[type-arg]
    *,
    bucket: int,
    top_n: int = ROUTE_METRICS_TOP_N,
) -> tuple[int, int, list[dict[str, Any]]]:
    key = f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:{bucket}"
    raw = client.hgetall(key) or {}
    decoded: dict[str, int] = {}
    for k, v in raw.items():
        k_str = k.decode("utf-8", errors="ignore") if isinstance(k, (bytes, bytearray)) else str(k)
        decoded[k_str] = _decode_int(v)

    golden_total = decoded.get("golden|_total", 0)
    legacy_total = decoded.get("legacy|_total", 0)

    legacy_rows: list[dict[str, Any]] = []
    for field, count in decoded.items():
        if not field.startswith("legacy|") or field == "legacy|_total":
            continue
        parts = field.split("|", 2)
        if len(parts) != 3:
            continue
        _, method, path = parts
        if method == "_total":
            continue
        legacy_rows.append({"route": f"{method} {path}", "count": int(count)})

    legacy_rows.sort(key=lambda item: int(item.get("count", 0)), reverse=True)
    return golden_total, legacy_total, legacy_rows[: max(0, int(top_n))]


@celery_app.task(name="tasks.monitoring.monitor_api_calls")  # type: ignore[misc]
def monitor_api_calls() -> Dict[str, Any]:
    settings = get_settings()
    client = _get_metrics_redis(settings)
    value = client.get("api_calls_per_minute")
    calls = (
        int(value) if value is not None and isinstance(value, (int, str, bytes)) else 0
    )

    if calls > API_CALL_THRESHOLD:
        _send_alert("warning", f"API 调用接近限制: {calls}/60")

    return {"api_calls_last_minute": calls, "threshold": API_CALL_THRESHOLD}


@celery_app.task(name="tasks.monitoring.monitor_cache_health")  # type: ignore[misc]
def monitor_cache_health() -> Dict[str, Any]:
    settings = get_settings()
    cache_manager = CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )

    async def _calculate() -> Dict[str, Any]:
        from app.db.session import SessionFactory
        from app.tasks.maintenance_task import (
            cleanup_expired_posts_hot_impl,
            collect_storage_metrics_impl,
        )

        async with SessionFactory() as db:
            loader = CommunityPoolLoader(db)
            communities = await loader.load_community_pool(force_refresh=False)
        seed_names = [
            profile.name for profile in communities if profile.tier.lower() == "seed"
        ]
        hit_rate = await cache_manager.calculate_cache_hit_rate(seed_names)

        # 实体提取率监控：过去60分钟的实体/帖子比
        entity_rate: float | None = None
        recent_posts = recent_entities = 0
        try:
            from sqlalchemy import text as sqltext
            cutoff_sql = "NOW() - INTERVAL '60 minutes'"
            async with SessionFactory() as db_metrics:
                res_posts = await db_metrics.execute(
                    sqltext(
                        "SELECT count(*) FROM posts_hot WHERE created_at >= "
                        + cutoff_sql
                    )
                )
                res_entities = await db_metrics.execute(
                    sqltext(
                        "SELECT count(*) FROM content_entities WHERE created_at >= "
                        + cutoff_sql
                    )
                )
                recent_posts = int(res_posts.scalar() or 0)
                recent_entities = int(res_entities.scalar() or 0)
                if recent_posts > 0:
                    entity_rate = recent_entities / recent_posts
                if recent_posts > 0 and entity_rate is not None and entity_rate < 0.1:
                    _send_alert(
                        "warning",
                        f"实体提取率偏低: entities/posts={entity_rate:.3f} ({recent_entities}/{recent_posts})",
                    )
        except Exception as exc:  # pragma: no cover - defensive
            _LOGGER.warning("实体提取率计算失败: %s", exc, exc_info=True)

        if seed_names and hit_rate < CACHE_HIT_THRESHOLD:
            percentage = round(hit_rate * 100, 2)
            _send_alert("warning", f"缓存命中率偏低: {percentage}%")

        cleanup: Dict[str, Any] | None = None
        metrics_snapshot: Dict[str, Any] | None = None
        try:
            cleanup, metrics_snapshot = await asyncio.gather(
                cleanup_expired_posts_hot_impl(),
                collect_storage_metrics_impl(),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            _LOGGER.warning("维护任务执行失败: %s", exc, exc_info=True)

        payload: Dict[str, Any] = {
            "seed_count": len(seed_names),
            "cache_hit_rate": hit_rate,
        }
        if entity_rate is not None:
            payload["entity_rate_60m"] = entity_rate
            payload["recent_posts_60m"] = recent_posts
            payload["recent_entities_60m"] = recent_entities
        if cleanup is not None:
            payload["cleanup_deleted"] = cleanup.get("deleted_count", 0)
        if metrics_snapshot is not None:
            payload["storage_metrics_id"] = metrics_snapshot.get("id")
        return payload

    # 统一使用全局事件循环以避免 “Future attached to a different loop”
    return run_coro(_calculate())


@celery_app.task(name="tasks.monitoring.monitor_crawler_health")  # type: ignore[misc]
def monitor_crawler_health() -> Dict[str, Any]:
    get_settings()

    async def _load() -> Dict[str, Any]:
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
        return {"stale_communities": [], "threshold_minutes": CRAWL_STALE_MINUTES}

    return run_coro(_load())


@celery_app.task(name="tasks.monitoring.monitor_facts_audit_cleanup")  # type: ignore[misc]
def monitor_facts_audit_cleanup() -> Dict[str, Any]:
    settings = get_settings()
    enabled = os.getenv("ENABLE_FACTS_AUDIT_CLEANUP", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    async def _load() -> Dict[str, Any]:
        from app.db.session import SessionFactory

        now = datetime.now(timezone.utc)
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
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        """
                    )
                )
                expired_snapshots = int(row.scalar() or 0)

            if has_run_logs:
                row = await db.execute(
                    text(
                        """
                        SELECT COUNT(*)::bigint
                        FROM facts_run_logs
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        """
                    )
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
def monitor_e2e_tests() -> Dict[str, Any]:
    settings = get_settings()
    metrics = _load_e2e_metrics()
    if metrics is None:
        _LOGGER.info("未找到端到端测试指标文件: %s", TEST_METRICS_PATH)
        return {"status": "missing"}

    runs = metrics.get("runs", [])
    total_runs = len(runs)
    failed_runs = sum(1 for run in runs if run.get("status") != "success")
    failure_rate = failed_runs / total_runs if total_runs else 0.0
    max_duration = max(
        (float(run.get("duration_seconds", 0)) for run in runs), default=0.0
    )

    if failure_rate > E2E_MAX_FAILURE_RATE:
        _send_alert(
            "error",
            f"端到端测试失败率 {failure_rate:.2%} 超过阈值 {E2E_MAX_FAILURE_RATE:.2%}",
        )

    if max_duration > E2E_MAX_DURATION:
        _send_alert(
            "warning",
            f"端到端测试最长耗时 {max_duration:.2f}s 超过阈值 {E2E_MAX_DURATION:.2f}s",
        )

    _update_dashboard(
        settings,
        {
            "e2e_runs": total_runs,
            "e2e_failures": failed_runs,
            "e2e_failure_rate": failure_rate,
            "e2e_max_duration": max_duration,
        },
    )

    return {
        "status": "ok",
        "runs": total_runs,
        "failed": failed_runs,
        "failure_rate": failure_rate,
        "max_duration": max_duration,
    }


@celery_app.task(name="tasks.monitoring.collect_test_logs")  # type: ignore[misc]
def collect_test_logs(max_lines: int = 200) -> Dict[str, Any]:
    settings = get_settings()
    if not TEST_LOG_PATH.exists():
        return {"status": "missing"}

    try:
        lines = TEST_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:
        _send_alert("warning", f"读取测试日志失败: {exc}")
        return {"status": "error", "message": str(exc)}

    tail = lines[-max_lines:]
    client = _get_metrics_redis(settings)
    key = "logs:test_e2e"
    if tail:
        client.delete(key)
        client.rpush(key, *tail)
        client.ltrim(key, 0, max_lines - 1)
        client.expire(key, 3600)
    return {"status": "ok", "lines": len(tail)}


@celery_app.task(name="tasks.monitoring.update_performance_dashboard")  # type: ignore[misc]
def update_performance_dashboard() -> Dict[str, Any]:
    settings = get_settings()
    metrics = _load_e2e_metrics() or {}
    client = _get_metrics_redis(settings)
    bucket = _route_metrics_bucket()
    golden_calls, legacy_calls, legacy_top = _load_route_call_metrics(
        client, bucket=bucket
    )
    payload = {
        "last_e2e_run": metrics.get("runs", [{}])[-1] if metrics.get("runs") else {},
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "golden_calls_last_minute": golden_calls,
        "legacy_calls_last_minute": legacy_calls,
    }
    if legacy_calls:
        payload["legacy_top_paths_last_minute"] = legacy_top
    _update_dashboard(settings, payload)
    return payload


@celery_app.task(name="tasks.monitoring.monitor_warmup_metrics")  # type: ignore[misc]
def monitor_warmup_metrics() -> Dict[str, Any]:
    """Monitor warmup period metrics (PRD-09 Day 13-20).

    Collects and monitors:
    - API call rate
    - Cache hit rate
    - Community pool size
    - System health

    Returns:
        dict: Warmup metrics summary
    """
    settings = get_settings()

    # Collect API call metrics
    api_metrics = monitor_api_calls()

    # Collect cache health metrics
    cache_metrics = monitor_cache_health()

    # Collect crawler health metrics
    crawler_metrics = monitor_crawler_health()

    # Get community pool size
    async def _get_pool_size() -> int:
        from app.db.session import SessionFactory

        async with SessionFactory() as db:
            loader = CommunityPoolLoader(db)
            communities = await loader.load_community_pool(force_refresh=False)
            return len(communities)

    pool_size = asyncio.run(_get_pool_size())

    # Aggregate metrics
    warmup_metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_calls_per_minute": api_metrics.get("api_calls_last_minute", 0),
        "cache_hit_rate": cache_metrics.get("cache_hit_rate", 0.0),
        "community_pool_size": pool_size,
        "stale_communities_count": len(crawler_metrics.get("stale_communities", [])),
    }

    # Update dashboard
    _update_dashboard(settings, {"warmup_metrics": warmup_metrics})

    # Check warmup period goals (PRD-09)
    if pool_size < 100:
        _send_alert("warning", f"社区池规模 {pool_size} 低于目标 100")

    if cache_metrics.get("cache_hit_rate", 0.0) < 0.85:
        hit_rate_pct = cache_metrics.get("cache_hit_rate", 0.0) * 100
        _send_alert("warning", f"缓存命中率 {hit_rate_pct:.1f}% 低于目标 85%")

    logger.info(
        "Warmup metrics: pool_size=%d, cache_hit_rate=%.2f%%, api_calls=%d",
        pool_size,
        cache_metrics.get("cache_hit_rate", 0.0) * 100,
        api_metrics.get("api_calls_last_minute", 0),
    )

    return warmup_metrics


@celery_app.task(name="tasks.monitoring.watchdog_stalled_tasks")  # type: ignore[misc]
def watchdog_stalled_tasks() -> Dict[str, Any]:
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

    # Best-effort categorization: if we can't see any worker, treat as dependency down.
    category = "worker_stalled"
    try:
        inspect = celery_app.control.inspect()
        ping = inspect.ping() if inspect is not None else None
        if not ping:
            category = "system_dependency_down"
    except Exception:  # pragma: no cover
        category = "system_dependency_down"

    async def _run() -> Dict[str, Any]:
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


@celery_app.task(name="tasks.monitoring.monitor_contract_health")  # type: ignore[misc]
def monitor_contract_health(hours: int | None = None) -> Dict[str, Any]:
    """
    Phase106-2: Contract health dashboard + alerting.

    Human goal:
    - Convert Phase105 "contract fields" into a practical ops dashboard.
    - Best-effort: metrics failure must not affect any request path.
    """
    settings = get_settings()
    window_hours = max(1, _as_int(hours, default=CONTRACT_HEALTH_WINDOW_HOURS))
    window = timedelta(hours=window_hours)
    now = datetime.now(timezone.utc)
    cutoff = now - window

    comments_not_used_rate_warn = _as_float(
        os.getenv("CONTRACT_HEALTH_ALERT_COMMENTS_NOT_USED_RATE_WARN", "0.10"),
        default=0.10,
    )
    x_blocked_rate_warn = _as_float(
        os.getenv("CONTRACT_HEALTH_ALERT_X_BLOCKED_RATE_WARN", "0.15"),
        default=0.15,
    )
    data_validation_error_count_warn = _as_int(
        os.getenv("CONTRACT_HEALTH_ALERT_DATA_VALIDATION_ERROR_COUNT_WARN", "1"),
        default=1,
    )
    thresholds = ContractHealthAlertThresholds(
        comments_not_used_rate_warn=comments_not_used_rate_warn,
        x_blocked_rate_warn=x_blocked_rate_warn,
        data_validation_error_count_warn=data_validation_error_count_warn,
    )

    async def _load() -> Dict[str, Any]:
        from app.db.session import SessionFactory
        from app.models.analysis import Analysis
        from app.models.task import Task as TaskModel

        async with SessionFactory() as session:
            result = await session.execute(
                select(
                    TaskModel.id,
                    TaskModel.status,
                    TaskModel.created_at,
                    TaskModel.started_at,
                    TaskModel.completed_at,
                    TaskModel.failure_category,
                    Analysis.sources,
                )
                .outerjoin(Analysis, Analysis.task_id == TaskModel.id)
                .where(TaskModel.created_at >= cutoff)
            )
            rows: list[ContractHealthRow] = []
            for (
                task_id,
                status,
                created_at,
                started_at,
                completed_at,
                failure_category,
                sources,
            ) in result.all():
                created = created_at or now
                status_value = getattr(status, "value", status)
                rows.append(
                    ContractHealthRow(
                        task_id=str(task_id),
                        status=str(status_value),
                        created_at=created,
                        started_at=started_at,
                        completed_at=completed_at,
                        failure_category=str(failure_category) if failure_category else None,
                        sources=dict(sources) if isinstance(sources, dict) else None,
                    )
                )

        report = compute_contract_health(rows=rows, now=now, window=window)
        alerts = evaluate_contract_health_alerts(report, thresholds=thresholds)
        return {
            "status": "ok",
            "generated_at": now.isoformat(),
            "window_hours": window_hours,
            "report": report,
            "alerts": [
                {
                    "level": alert.level,
                    "code": alert.code,
                    "message": alert.message,
                    "details": dict(alert.details),
                }
                for alert in alerts
            ],
        }

    try:
        payload = run_coro(_load())
    except Exception as exc:  # pragma: no cover - defensive
        _send_alert("error", f"contract_health 聚合失败: {exc}")
        return {"status": "error", "message": str(exc)}

    # Write dashboard snapshot (best-effort).
    _update_dashboard(settings, {"contract_health": payload})

    # Alerting (best-effort): write both logs and audit events for traceability.
    alerts_raw = payload.get("alerts") or []
    if isinstance(alerts_raw, list) and alerts_raw:
        for raw in alerts_raw[:20]:
            if not isinstance(raw, dict):
                continue
            level = str(raw.get("level") or "warning")
            code = str(raw.get("code") or "unknown")
            message = str(raw.get("message") or "")
            _send_alert(level, f"contract_health[{code}]: {message}")

        async def _audit() -> None:
            from app.db.session import SessionFactory

            async with SessionFactory() as session:
                for raw in alerts_raw[:20]:
                    if not isinstance(raw, dict):
                        continue
                    code = str(raw.get("code") or "unknown")
                    await session.execute(
                        text(
                            """
                            INSERT INTO data_audit_events (
                                event_type, target_type, target_id, reason, source_component, new_value
                            )
                            VALUES (
                                'monitor', 'system', 'contract_health', :reason, 'monitor_contract_health',
                                CAST(:payload AS JSONB)
                            )
                            """
                        ),
                        {
                            "reason": code,
                            "payload": json.dumps(
                                {
                                    "generated_at": payload.get("generated_at"),
                                    "window_hours": payload.get("window_hours"),
                                    "alert": raw,
                                },
                                ensure_ascii=False,
                            ),
                        },
                    )
                await session.commit()

        try:
            run_coro(_audit())
        except Exception:
            pass

    return payload
