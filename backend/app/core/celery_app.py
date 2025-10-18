"""
Celery application bootstrap aligned with PRD-04: 任务系统架构.

Key responsibilities:
    * Provide a single Celery instance with Redis broker/backend defaults.
    * Honour dynamic worker concurrency configuration (min(cpu_cores, 4)).
    * Expose configuration required for retry semantics and task routing.
    * Use 'solo' pool on macOS to avoid fork() + Objective-C runtime crashes.

The module exports both `celery_app` and `app` for CLI compatibility:
    celery -A app.core.celery_app worker --loglevel=info --pool=solo
"""

from __future__ import annotations

import multiprocessing
import os
from typing import Any, Dict

from celery import Celery  # type: ignore[import-untyped]
from kombu import Queue  # type: ignore[import-untyped]

DEFAULT_BROKER_URL = "redis://localhost:6379/1"
DEFAULT_BACKEND_URL = "redis://localhost:6379/2"
DEFAULT_QUEUE_NAMES = (
    "analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue"
)


def _split_queue_names(raw: str) -> list[str]:
    return [name.strip() for name in raw.split(",") if name.strip()]


def _get_worker_count() -> int:
    configured = os.getenv("CELERY_WORKER_COUNT")
    if configured:
        try:
            value = int(configured)
            if value > 0:
                return value
        except ValueError:
            pass

    try:
        cpu_count = multiprocessing.cpu_count()
    except NotImplementedError:
        cpu_count = 1

    return max(1, min(cpu_count, 4))


def _build_conf() -> Dict[str, Any]:
    queues = _split_queue_names(os.getenv("CELERY_QUEUE_NAMES", DEFAULT_QUEUE_NAMES))
    task_queues = tuple(Queue(name) for name in queues) if queues else ()
    default_queue = queues[0] if queues else "celery"

    task_routes: Dict[str, Dict[str, str]] = {}
    if default_queue:
        task_routes["tasks.analysis.run"] = {"queue": default_queue}
    task_routes.setdefault("tasks.crawler.crawl_community", {"queue": "crawler_queue"})
    task_routes.setdefault(
        "tasks.crawler.crawl_seed_communities", {"queue": "crawler_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_api_calls", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_cache_health", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_crawler_health", {"queue": "monitoring_queue"}
    )

    return {
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_default_retry_delay": int(os.getenv("CELERY_RETRY_DELAY", "60")),
        "task_max_retries": int(os.getenv("CELERY_MAX_RETRIES", "3")),
        "worker_concurrency": _get_worker_count(),
        "worker_prefetch_multiplier": int(os.getenv("CELERY_PREFETCH_MULTIPLIER", "1")),
        "task_queues": task_queues,
        "task_default_queue": default_queue,
        "task_routes": task_routes,
    }


celery_app = Celery(
    "reddit_signal_scanner",
    broker=os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", DEFAULT_BACKEND_URL),
)

from celery.schedules import crontab  # type: ignore[import-untyped]

celery_app.conf.update(_build_conf())
celery_app.autodiscover_tasks(["app.tasks"], force=True)

celery_app.conf.beat_schedule = {
    # Warmup 批量爬取：每 2 小时执行一次，保证冷启动覆盖
    "warmup-crawl-seed-communities": {
        "task": "tasks.crawler.crawl_seed_communities",
        "schedule": crontab(minute="0", hour="*/2"),
        "options": {"queue": "crawler_queue"},
    },
    # 兼容旧版批量抓取（半小时一次），供手动触发和回滚兜底
    "crawl-seed-communities": {
        "task": "tasks.crawler.crawl_seed_communities",
        "schedule": crontab(minute="0,30"),
        "options": {"queue": "crawler_queue"},
    },
    # 增量抓取：每 30 分钟执行一次（冷热双写 + 水位线）
    "auto-crawl-incremental": {
        "task": "tasks.crawler.crawl_seed_communities_incremental",
        "schedule": crontab(minute="0,30"),  # 每 30 分钟执行一次
        "options": {"queue": "crawler_queue", "expires": 1800},
    },
    # 启动后 5 分钟触发一次增量抓取，避免等待整点
    # 注意：Celery Beat 不支持 one_off 参数，暂时注释掉
    # TODO: 考虑在 Worker 启动时通过 worker_ready signal 手动触发
    # "auto-crawl-incremental-bootstrap": {
    #     "task": "tasks.crawler.crawl_seed_communities_incremental",
    #     "schedule": 300.0,  # 5 minutes
    #     "options": {"queue": "crawler_queue", "expires": 900},
    # },
    # Monitoring tasks (PRD-09 warmup period monitoring)
    "monitor-warmup-metrics": {
        "task": "tasks.monitoring.monitor_warmup_metrics",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "monitor-api-calls": {
        "task": "tasks.monitoring.monitor_api_calls",
        "schedule": crontab(minute="*"),
    },
    "monitor-cache-health": {
        "task": "tasks.monitoring.monitor_cache_health",
        "schedule": crontab(minute="*/5"),
    },
    "monitor-crawler-health": {
        "task": "tasks.monitoring.monitor_crawler_health",
        "schedule": crontab(minute="*/10"),
    },
    "monitor-e2e-tests": {
        "task": "tasks.monitoring.monitor_e2e_tests",
        "schedule": crontab(minute="*/10"),
    },
    "collect-test-logs": {
        "task": "tasks.monitoring.collect_test_logs",
        "schedule": crontab(minute="*/5"),
    },
    "update-performance-dashboard": {
        "task": "tasks.monitoring.update_performance_dashboard",
        "schedule": crontab(minute="*/15"),
    },
}

# Import ensures registration even when autodiscovery is executed in tooling
# contexts (e.g. verify_celery_config.py) where lazy loading might skip it.
try:
    from app.tasks import analysis_task as _analysis_task  # noqa: F401
    from app.tasks import crawler_task as _crawler_task  # noqa: F401
    from app.tasks import monitoring_task as _monitoring_task  # noqa: F401
    from app.tasks import warmup_crawler as _warmup_crawler  # noqa: F401
except Exception:  # pragma: no cover - defensive guard for diagnostics
    pass

# Expose alias expected by `celery -A app.core.celery_app ...`.
app = celery_app

__all__ = ["celery_app", "app"]
