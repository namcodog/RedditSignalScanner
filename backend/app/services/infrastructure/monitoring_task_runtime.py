from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

import redis

from app.core.config import Settings
from app.schemas.monitoring import CacheHealthResult, ContractHealthResult
from app.services.community.community_pool_loader import CommunityPoolLoader
from app.services.infrastructure.cache_manager import CacheManager


async def calculate_monitor_cache_health(
    *,
    cache_manager: CacheManager,
    cache_hit_threshold: float,
    utc_now: Callable[[], datetime],
    send_alert: Callable[[str, str], None],
    logger: Any,
    load_cache_seed_names: Callable[[], Awaitable[list[str]]],
    load_entity_extraction_metrics: Callable[..., Awaitable[dict[str, Any]]],
    mark_payload_degraded: Callable[..., None],
    run_cache_maintenance_tasks: Callable[[], Awaitable[dict[str, dict[str, Any] | None]]],
) -> CacheHealthResult:
    seed_names = await load_cache_seed_names()
    hit_rate = await cache_manager.calculate_cache_hit_rate(seed_names)

    payload = CacheHealthResult(
        status="ok",
        generated_at=utc_now(),
        seed_count=len(seed_names),
        cache_hit_rate=hit_rate,
    )

    if seed_names and hit_rate < cache_hit_threshold:
        percentage = round(hit_rate * 100, 2)
        send_alert("warning", f"缓存命中率偏低: {percentage}%")

    try:
        entity_metrics = await load_entity_extraction_metrics(
            cutoff=utc_now() - timedelta(minutes=60)
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("实体提取率计算失败: %s", exc, exc_info=True)
        mark_payload_degraded(
            payload,
            code="entity_rate_unavailable",
            message=str(exc),
        )
    else:
        entity_rate = entity_metrics["entity_rate"]
        recent_posts = int(entity_metrics["recent_posts"])
        recent_entities = int(entity_metrics["recent_entities"])
        if entity_rate is not None:
            payload.entity_rate_60m = entity_rate
        payload.recent_posts_60m = recent_posts
        payload.recent_entities_60m = recent_entities
        if recent_posts > 0 and entity_rate is not None and entity_rate < 0.1:
            send_alert(
                "warning",
                f"实体提取率偏低: entities/posts={entity_rate:.3f} ({recent_entities}/{recent_posts})",
            )

    try:
        maintenance = await run_cache_maintenance_tasks()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("维护任务执行失败: %s", exc, exc_info=True)
        mark_payload_degraded(
            payload,
            code="maintenance_tasks_failed",
            message=str(exc),
        )
    else:
        cleanup = maintenance.get("cleanup")
        metrics_snapshot = maintenance.get("metrics_snapshot")
        if cleanup is not None:
            payload.cleanup_deleted = cleanup.get("deleted_count", 0)
        if metrics_snapshot is not None:
            payload.storage_metrics_id = metrics_snapshot.get("id")

    return payload


def run_monitor_api_calls(
    *,
    settings: Settings,
    api_call_threshold: int,
    get_metrics_redis: Callable[[Settings], redis.Redis],  # type: ignore[type-arg]
    send_alert: Callable[[str, str], None],
) -> dict[str, Any]:
    client = get_metrics_redis(settings)
    value = client.get("api_calls_per_minute")
    calls = (
        int(value) if value is not None and isinstance(value, (int, str, bytes)) else 0
    )
    if calls > api_call_threshold:
        send_alert("warning", f"API 调用接近限制: {calls}/60")
    return {"api_calls_last_minute": calls, "threshold": api_call_threshold}


def run_monitor_cache_health(
    *,
    settings: Settings,
    cache_manager_factory: Callable[..., CacheManager],
    run_coro: Callable[[Awaitable[CacheHealthResult]], CacheHealthResult],
    calculate_cache_health: Callable[..., Awaitable[CacheHealthResult]],
    serialize_result: Callable[[Any], dict[str, Any]],
    build_error_result: Callable[..., dict[str, Any]],
    send_alert: Callable[[str, str], None],
) -> dict[str, Any]:
    cache_manager = cache_manager_factory(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )
    try:
        result = run_coro(calculate_cache_health(cache_manager=cache_manager))
        return serialize_result(result)
    except Exception as exc:  # pragma: no cover - defensive
        send_alert("error", f"缓存健康监控失败: {exc}")
        return build_error_result(message=str(exc))


def run_update_performance_dashboard(
    *,
    settings: Settings,
    load_e2e_metrics: Callable[[], dict[str, Any] | None],
    get_metrics_redis: Callable[[Settings], redis.Redis],  # type: ignore[type-arg]
    route_metrics_bucket: Callable[[], int],
    load_route_call_metrics: Callable[..., tuple[int, int, list[dict[str, Any]]]],
    update_dashboard: Callable[[Settings, dict[str, Any]], None],
    route_metrics_top_n: int,
) -> dict[str, Any]:
    metrics = load_e2e_metrics() or {}
    client = get_metrics_redis(settings)
    bucket = route_metrics_bucket()
    golden_calls, legacy_calls, legacy_top = load_route_call_metrics(
        client,
        bucket=bucket,
        top_n=route_metrics_top_n,
    )
    payload: dict[str, Any] = {
        "last_e2e_run": metrics.get("runs", [{}])[-1] if metrics.get("runs") else {},
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "golden_calls_last_minute": golden_calls,
        "legacy_calls_last_minute": legacy_calls,
    }
    if legacy_calls:
        payload["legacy_top_paths_last_minute"] = legacy_top
    update_dashboard(settings, payload)
    return payload


def run_monitor_e2e_tests(
    *,
    settings: Settings,
    load_e2e_metrics: Callable[[], dict[str, Any] | None],
    send_alert: Callable[[str, str], None],
    update_dashboard: Callable[[Settings, dict[str, Any]], None],
    max_failure_rate: float,
    max_duration: float,
) -> dict[str, Any]:
    metrics = load_e2e_metrics()
    if metrics is None:
        return {"status": "missing"}

    runs = metrics.get("runs", [])
    total_runs = len(runs)
    failed_runs = sum(1 for run in runs if run.get("status") != "success")
    failure_rate = failed_runs / total_runs if total_runs else 0.0
    current_max_duration = max(
        (float(run.get("duration_seconds", 0)) for run in runs),
        default=0.0,
    )

    if failure_rate > max_failure_rate:
        send_alert(
            "error",
            f"端到端测试失败率 {failure_rate:.2%} 超过阈值 {max_failure_rate:.2%}",
        )

    if current_max_duration > max_duration:
        send_alert(
            "warning",
            f"端到端测试最长耗时 {current_max_duration:.2f}s 超过阈值 {max_duration:.2f}s",
        )

    update_dashboard(
        settings,
        {
            "e2e_runs": total_runs,
            "e2e_failures": failed_runs,
            "e2e_failure_rate": failure_rate,
            "e2e_max_duration": current_max_duration,
        },
    )
    return {
        "status": "ok",
        "runs": total_runs,
        "failed": failed_runs,
        "failure_rate": failure_rate,
        "max_duration": current_max_duration,
    }


def run_collect_test_logs(
    *,
    settings: Settings,
    test_log_path: Path,
    max_lines: int,
    get_metrics_redis: Callable[[Settings], redis.Redis],  # type: ignore[type-arg]
    send_alert: Callable[[str, str], None],
) -> dict[str, Any]:
    if not test_log_path.exists():
        return {"status": "missing"}

    try:
        lines = test_log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:
        send_alert("warning", f"读取测试日志失败: {exc}")
        return {"status": "error", "message": str(exc)}

    tail = lines[-max_lines:]
    client = get_metrics_redis(settings)
    key = "logs:test_e2e"
    if tail:
        client.delete(key)
        client.rpush(key, *tail)
        client.ltrim(key, 0, max_lines - 1)
        client.expire(key, 3600)
    return {"status": "ok", "lines": len(tail)}


async def load_community_pool_size(
    *,
    session_factory: Callable[[], Any],
    community_pool_loader_cls: type[CommunityPoolLoader],
) -> int:
    async with session_factory() as db:
        loader = community_pool_loader_cls(db)
        communities = await loader.load_community_pool(force_refresh=False)
        return len(communities)


def run_monitor_warmup_metrics(
    *,
    settings: Settings,
    monitor_api_calls: Callable[[], dict[str, Any]],
    monitor_cache_health: Callable[[], dict[str, Any]],
    monitor_crawler_health: Callable[[], dict[str, Any]],
    run_coro: Callable[[Awaitable[int]], int],
    load_community_pool_size: Callable[[], Awaitable[int]],
    update_dashboard: Callable[[Settings, dict[str, Any]], None],
    send_alert: Callable[[str, str], None],
) -> dict[str, Any]:
    api_metrics = monitor_api_calls()
    cache_metrics = monitor_cache_health()
    crawler_metrics = monitor_crawler_health()
    pool_size = run_coro(load_community_pool_size())

    warmup_metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_calls_per_minute": api_metrics.get("api_calls_last_minute", 0),
        "cache_hit_rate": cache_metrics.get("cache_hit_rate", 0.0),
        "community_pool_size": pool_size,
        "stale_communities_count": len(crawler_metrics.get("stale_communities", [])),
    }

    update_dashboard(settings, {"warmup_metrics": warmup_metrics})

    if pool_size < 100:
        send_alert("warning", f"社区池规模 {pool_size} 低于目标 100")

    if cache_metrics.get("cache_hit_rate", 0.0) < 0.85:
        hit_rate_pct = cache_metrics.get("cache_hit_rate", 0.0) * 100
        send_alert("warning", f"缓存命中率 {hit_rate_pct:.1f}% 低于目标 85%")

    return warmup_metrics


def run_monitor_contract_health(
    *,
    settings: Settings,
    hours: int | None,
    as_int: Callable[..., int],
    as_float: Callable[..., float],
    default_window_hours: int,
    utc_now: Callable[[], datetime],
    build_contract_health_thresholds: Callable[..., Any],
    run_coro: Callable[[Awaitable[ContractHealthResult]], ContractHealthResult],
    build_contract_health_result: Callable[..., Awaitable[ContractHealthResult]],
    finalize_contract_health_result: Callable[..., ContractHealthResult],
    update_dashboard: Callable[[Settings, dict[str, Any]], None],
    send_alert: Callable[[str, str], None],
    write_contract_health_audit_events: Callable[..., Awaitable[None]],
    build_error_result: Callable[..., dict[str, Any]],
    serialize_result: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    window_hours = max(1, as_int(hours, default=default_window_hours))
    window = timedelta(hours=window_hours)
    now = utc_now()
    cutoff = now - window
    thresholds = build_contract_health_thresholds(
        as_float=as_float,
        as_int=as_int,
    )

    try:
        result = run_coro(
            build_contract_health_result(
                window_hours=window_hours,
                now=now,
                window=window,
                cutoff=cutoff,
                thresholds=thresholds,
            )
        )
    except Exception as exc:  # pragma: no cover - defensive
        send_alert("error", f"contract_health 聚合失败: {exc}")
        return build_error_result(message=str(exc))

    finalized = finalize_contract_health_result(
        result=result,
        settings=settings,
        update_dashboard=update_dashboard,
        send_alert=send_alert,
        write_audit_events=lambda payload, alerts: run_coro(
            write_contract_health_audit_events(payload, alerts)
        ),
    )
    return serialize_result(finalized)


def build_monitoring_runtime_dependencies(
    *,
    get_metrics_redis: Callable[[Settings], redis.Redis],  # type: ignore[type-arg]
    send_alert: Callable[[str, str], None],
    load_e2e_metrics: Callable[[], dict[str, Any] | None],
    update_dashboard: Callable[[Settings, dict[str, Any]], None],
    route_metrics_bucket: Callable[[], int],
    load_route_call_metrics: Callable[..., tuple[int, int, list[dict[str, Any]]]],
    cache_manager_factory: Callable[..., CacheManager],
    run_coro: Callable[[Awaitable[Any]], Any],
    calculate_cache_health: Callable[..., Awaitable[CacheHealthResult]],
    build_error_result: Callable[..., dict[str, Any]],
    serialize_result: Callable[[Any], dict[str, Any]],
    as_int: Callable[..., int],
    as_float: Callable[..., float],
    utc_now: Callable[[], datetime],
    build_contract_health_thresholds: Callable[..., Any],
    build_contract_health_result: Callable[..., Awaitable[ContractHealthResult]],
    finalize_contract_health_result: Callable[..., ContractHealthResult],
    write_contract_health_audit_events: Callable[..., Awaitable[None]],
    load_community_pool_size: Callable[[], Awaitable[int]],
) -> SimpleNamespace:
    return SimpleNamespace(
        get_metrics_redis=get_metrics_redis,
        send_alert=send_alert,
        load_e2e_metrics=load_e2e_metrics,
        update_dashboard=update_dashboard,
        route_metrics_bucket=route_metrics_bucket,
        load_route_call_metrics=load_route_call_metrics,
        cache_manager_factory=cache_manager_factory,
        run_coro=run_coro,
        calculate_cache_health=calculate_cache_health,
        build_error_result=build_error_result,
        serialize_result=serialize_result,
        as_int=as_int,
        as_float=as_float,
        utc_now=utc_now,
        build_contract_health_thresholds=build_contract_health_thresholds,
        build_contract_health_result=build_contract_health_result,
        finalize_contract_health_result=finalize_contract_health_result,
        write_contract_health_audit_events=write_contract_health_audit_events,
        load_community_pool_size=load_community_pool_size,
    )


__all__ = [
    "build_monitoring_runtime_dependencies",
    "calculate_monitor_cache_health",
    "load_community_pool_size",
    "run_collect_test_logs",
    "run_monitor_api_calls",
    "run_monitor_cache_health",
    "run_monitor_contract_health",
    "run_monitor_e2e_tests",
    "run_monitor_warmup_metrics",
    "run_update_performance_dashboard",
]
