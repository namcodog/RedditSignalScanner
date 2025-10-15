from __future__ import annotations

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import redis
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models.community_cache import CommunityCache
from app.services.cache_manager import CacheManager
from app.services.community_pool_loader import CommunityPoolLoader

logger = get_task_logger(__name__)
_LOGGER = logging.getLogger(__name__)

API_CALL_THRESHOLD = int(os.getenv("MONITOR_API_THRESHOLD", "55"))
CACHE_HIT_THRESHOLD = float(os.getenv("MONITOR_CACHE_HIT_THRESHOLD", "0.70"))
CRAWL_STALE_MINUTES = int(os.getenv("MONITOR_CRAWL_STALE_MINUTES", "90"))
METRICS_REDIS_URL = os.getenv("MONITOR_REDIS_URL")
TEST_LOG_PATH = Path(os.getenv("TEST_LOG_PATH", "tmp/test_runs/e2e.log"))
TEST_METRICS_PATH = Path(os.getenv("TEST_METRICS_PATH", "tmp/test_runs/e2e_metrics.json"))
E2E_MAX_DURATION = float(os.getenv("E2E_MAX_DURATION_SECONDS", "300"))
E2E_MAX_FAILURE_RATE = float(os.getenv("E2E_MAX_FAILURE_RATE", "0.05"))
PERFORMANCE_DASHBOARD_KEY = os.getenv("PERFORMANCE_DASHBOARD_KEY", "dashboard:performance")


def _get_metrics_redis(settings: Settings) -> redis.Redis:
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
    enriched = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in values.items()}
    client.hset(PERFORMANCE_DASHBOARD_KEY, mapping=enriched)
    client.hset(PERFORMANCE_DASHBOARD_KEY, "updated_at", datetime.now(timezone.utc).isoformat())


@celery_app.task(name="tasks.monitoring.monitor_api_calls")
def monitor_api_calls() -> Dict[str, Any]:
    settings = get_settings()
    client = _get_metrics_redis(settings)
    value = client.get("api_calls_per_minute")
    calls = int(value) if value is not None else 0

    if calls > API_CALL_THRESHOLD:
        _send_alert("warning", f"API 调用接近限制: {calls}/60")

    return {"api_calls_last_minute": calls, "threshold": API_CALL_THRESHOLD}


@celery_app.task(name="tasks.monitoring.monitor_cache_health")
def monitor_cache_health() -> Dict[str, Any]:
    settings = get_settings()
    loader = CommunityPoolLoader()
    cache_manager = CacheManager(
        redis_url=settings.reddit_cache_redis_url,
        cache_ttl_seconds=settings.reddit_cache_ttl_seconds,
    )

    async def _calculate() -> Dict[str, Any]:
        communities = await loader.load_community_pool(force_refresh=False)
        seed_names = [profile.name for profile in communities if profile.tier.lower() == "seed"]
        hit_rate = cache_manager.calculate_cache_hit_rate(seed_names)

        if seed_names and hit_rate < CACHE_HIT_THRESHOLD:
            percentage = round(hit_rate * 100, 2)
            _send_alert("warning", f"缓存命中率偏低: {percentage}%")

        return {"seed_count": len(seed_names), "cache_hit_rate": hit_rate}

    return asyncio.run(_calculate())


@celery_app.task(name="tasks.monitoring.monitor_crawler_health")
def monitor_crawler_health() -> Dict[str, Any]:
    settings = get_settings()

    async def _load() -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=CRAWL_STALE_MINUTES)
        async for session in get_session():
            result = await session.execute(
                select(CommunityCache.community_name, CommunityCache.last_crawled_at).where(
                    CommunityCache.last_crawled_at < cutoff
                )
            )
            rows = result.all()
            stale = [
                {
                    "community": row.community_name,
                    "last_crawled_at": row.last_crawled_at.isoformat() if row.last_crawled_at else None,
                }
                for row in rows
            ]
            if stale:
                _send_alert(
                    "warning",
                    f"{len(stale)} 个社区超过 {CRAWL_STALE_MINUTES} 分钟未刷新",
                )
            return {"stale_communities": stale, "threshold_minutes": CRAWL_STALE_MINUTES}
        return {"stale_communities": [], "threshold_minutes": CRAWL_STALE_MINUTES}

    return asyncio.run(_load())


@celery_app.task(name="tasks.monitoring.monitor_e2e_tests")
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
    max_duration = max((float(run.get("duration_seconds", 0)) for run in runs), default=0.0)

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


@celery_app.task(name="tasks.monitoring.collect_test_logs")
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


@celery_app.task(name="tasks.monitoring.update_performance_dashboard")
def update_performance_dashboard() -> Dict[str, Any]:
    settings = get_settings()
    metrics = _load_e2e_metrics() or {}
    payload = {
        "last_e2e_run": metrics.get("runs", [{}])[-1] if metrics.get("runs") else {},
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _update_dashboard(settings, payload)
    return payload


__all__ = [
    "monitor_api_calls",
    "monitor_cache_health",
    "monitor_crawler_health",
    "monitor_e2e_tests",
    "collect_test_logs",
    "update_performance_dashboard",
]
