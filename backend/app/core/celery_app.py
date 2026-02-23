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

import logging
import multiprocessing
import os
from typing import Any, Dict

from celery import Celery  # type: ignore[import-untyped]
from celery.signals import worker_ready  # type: ignore[import-untyped]
from kombu import Queue  # type: ignore[import-untyped]

DEFAULT_BROKER_URL = "redis://localhost:6379/1"
DEFAULT_BACKEND_URL = "redis://localhost:6379/2"
DEFAULT_QUEUE_NAMES = (
    "analysis_queue,patrol_queue,backfill_queue,backfill_posts_queue_v2,probe_queue,compensation_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue"
)
BACKFILL_POSTS_QUEUE = os.getenv("BACKFILL_POSTS_QUEUE", "backfill_posts_queue_v2")
COMMENTS_BACKFILL_QUEUE = os.getenv("COMMENTS_BACKFILL_QUEUE", "backfill_queue")


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

    # 限制最大 Worker 数为 2，避免 Reddit API 速率限制冲突
    return max(1, min(cpu_count, 2))


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
        "tasks.crawler.crawl_seed_communities_incremental", {"queue": "patrol_queue"}
    )
    task_routes.setdefault(
        "tasks.crawler.crawl_low_quality_communities", {"queue": "patrol_queue"}
    )
    task_routes.setdefault("tasks.crawler.execute_target", {"queue": "crawler_queue"})
    task_routes.setdefault(
        "tasks.crawler.backfill_posts_window", {"queue": BACKFILL_POSTS_QUEUE}
    )
    task_routes.setdefault(
        "tasks.crawler.ingest_jsonl_backfill", {"queue": BACKFILL_POSTS_QUEUE}
    )
    # Spec014 comments/posts tasks
    task_routes.setdefault("comments.ingest_post_comments", {"queue": "crawler_queue"})
    task_routes.setdefault("comments.fetch_and_ingest", {"queue": "crawler_queue"})
    task_routes.setdefault("comments.backfill_full", {"queue": COMMENTS_BACKFILL_QUEUE})
    task_routes.setdefault(
        "comments.backfill_recent_full_daily", {"queue": COMMENTS_BACKFILL_QUEUE}
    )
    task_routes.setdefault("comments.label_comments", {"queue": "crawler_queue"})
    task_routes.setdefault("posts.label_recent", {"queue": "maintenance_queue"})
    task_routes.setdefault("subreddit.capture_snapshot_daily", {"queue": "crawler_queue"})
    task_routes.setdefault(
        "tasks.monitoring.monitor_api_calls", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_warmup_metrics", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_cache_health", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_crawler_health", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_facts_audit_cleanup", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.monitoring.monitor_contract_health", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.metrics.generate_daily", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.maintenance.collect_storage_metrics", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.maintenance.archive_old_posts", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.maintenance.check_storage_capacity", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.embedding.backfill_posts_batch", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.embedding.backfill_posts_full", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.embedding.backfill_comments_batch", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.embedding.backfill_comments_full", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.semantic.extract_candidates", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.llm.label_posts_batch", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.llm.label_comments_batch", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.llm.backfill_legacy_labels", {"queue": "maintenance_queue"}
    )
    task_routes.setdefault(
        "tasks.tier.generate_daily_suggestions", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.tier.emit_daily_suggestion_decision_units", {"queue": "monitoring_queue"}
    )
    task_routes.setdefault(
        "tasks.discovery.discover_new_communities_weekly", {"queue": "probe_queue"}
    )
    task_routes.setdefault("tasks.discovery.run_semantic_discovery", {"queue": "probe_queue"})
    task_routes.setdefault(
        "tasks.discovery.run_community_evaluation", {"queue": "probe_queue"}
    )
    task_routes.setdefault("tasks.probe.run_search_probe", {"queue": "probe_queue"})
    task_routes.setdefault("tasks.probe.run_hot_probe", {"queue": "probe_queue"})

    return {
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        # Reliability hardening (Spec013)
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        # Broker/dispatch 超时（Phase106）
        # 大白话：broker 掉线时，不要让 API/worker 卡很久；快速失败才可运营。
        "broker_transport_options": {
            "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600")),
            # Kombu Redis transport options
            "socket_connect_timeout": float(
                os.getenv("CELERY_BROKER_SOCKET_CONNECT_TIMEOUT", "2.0")
            ),
            "socket_timeout": float(os.getenv("CELERY_BROKER_SOCKET_TIMEOUT", "5.0")),
            "retry_on_timeout": True,
        },
        "result_expires": int(os.getenv("CELERY_RESULT_EXPIRES", str(6 * 3600))),
        "worker_max_tasks_per_child": int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", "100")),
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

from celery.schedules import crontab

celery_app.conf.update(_build_conf())
celery_app.autodiscover_tasks(["app.tasks"], force=True)

# 调度策略收敛 (Convergence):
# 移除了所有硬编码的 warmup/full-crawl 任务。
# 仅保留 'tick-tiered-crawl' 作为核心心跳，通过 TieredScheduler 和 DB 状态
# 智能判断哪些社区需要抓取 (T1/T2/T3 分级)。
celery_app.conf.beat_schedule = {
    # Core Crawler Tick: 每 30 分钟检查一次所有社区的水位线
    # 逻辑：Loader.get_due_communities() 会自动筛选出 (Now > LastCrawled + Frequency) 的社区
    "tick-tiered-crawl": {
        "task": "tasks.crawler.crawl_seed_communities_incremental",
        "schedule": crontab(minute="0,30"),  # 每 30 分钟触发一次心跳
        "options": {"queue": "patrol_queue", "expires": 1800},
    },
    
    # 精准补抓低质量社区：每 4 小时执行一次（T1.8）
    "crawl-low-quality-communities": {
        "task": "tasks.crawler.crawl_low_quality_communities",
        "schedule": crontab(minute="0", hour="*/4"),
        "options": {"queue": "patrol_queue", "expires": 3600},
    },

    # Backfill bootstrap (status-driven)
    "plan-backfill-bootstrap": {
        "task": "tasks.crawler.plan_backfill_bootstrap",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "backfill_queue", "expires": 3600},
    },

    # Seed sampling for DONE_CAPPED
    "plan-seed-sampling": {
        "task": "tasks.crawler.plan_seed_sampling",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "backfill_queue", "expires": 3600},
    },

    # Dispatch crawler task outbox
    "dispatch-task-outbox": {
        "task": "tasks.crawler.dispatch_task_outbox",
        "schedule": crontab(minute="*"),
        "options": {"queue": "backfill_queue", "expires": 60},
    },
    
    # Monitoring & Metrics
    "monitor-warmup-metrics": {
        "task": "tasks.monitoring.monitor_warmup_metrics",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "monitoring_queue"},
    },
    "generate-daily-metrics": {
        "task": "tasks.metrics.generate_daily",
        "schedule": crontab(hour="0", minute="0"),
        "options": {"queue": "monitoring_queue"},
    },
    "monitor-api-calls": {
        "task": "tasks.monitoring.monitor_api_calls",
        "schedule": crontab(minute="*"),
        "options": {"queue": "monitoring_queue"},
    },
    "monitor-cache-health": {
        "task": "tasks.monitoring.monitor_cache_health",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "monitoring_queue"},
    },
    "monitor-facts-audit": {
        "task": "tasks.monitoring.monitor_facts_audit_cleanup",
        "schedule": crontab(minute="40", hour="4"),
        "options": {"queue": "monitoring_queue"},
    },
    "monitor-crawler-health": {
        "task": "tasks.monitoring.monitor_crawler_health",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "monitoring_queue"},
    },
    "monitor-contract-health": {
        "task": "tasks.monitoring.monitor_contract_health",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "monitoring_queue", "expires": 300},
    },
    "watchdog-stalled-tasks": {
        "task": "tasks.monitoring.watchdog_stalled_tasks",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "monitoring_queue", "expires": 300},
    },
    
    # Maintenance (Cleanup & Sync)
    "sync-community-member-counts": {
        "task": "tasks.community.sync_member_counts",
        "schedule": crontab(hour="*/12", minute="0"),
        "options": {"queue": "crawler_queue", "expires": 7200},
    },
    "refresh-posts-latest": {
        "task": "tasks.maintenance.refresh_posts_latest",
        "schedule": crontab(minute="5"),
        "options": {"queue": "maintenance_queue", "expires": 1800},
    },
    "refresh-post-comment-stats": {
        "task": "tasks.maintenance.refresh_post_comment_stats",
        "schedule": crontab(minute="25"),
        "options": {"queue": "maintenance_queue", "expires": 1800},
    },
    "refresh-mv-monthly-trend": {
        "task": "tasks.maintenance.refresh_mv_monthly_trend",
        "schedule": crontab(minute="15", hour="2"),
        "options": {"queue": "maintenance_queue", "expires": 1800},
    },
    "refresh-mining-views": {
        "task": "tasks.maintenance.refresh_mining_views",
        "schedule": crontab(minute="35", hour="2"),
        "options": {"queue": "maintenance_queue", "expires": 1800},
    },
    "cleanup-expired-posts-hot": {
        "task": "tasks.maintenance.cleanup_expired_posts_hot",
        "schedule": crontab(minute="0", hour="4"),
        "options": {"queue": "cleanup_queue", "expires": 3600},
    },
    "cleanup-old-posts": {
        "task": "tasks.maintenance.cleanup_old_posts",
        "schedule": crontab(minute="30", hour="3"),
        "options": {"queue": "cleanup_queue", "expires": 7200},
    },
    "cleanup-expired-facts-audit": {
        "task": "tasks.maintenance.cleanup_expired_facts_audit",
        "schedule": crontab(minute="20", hour="4"),
        "options": {"queue": "cleanup_queue", "expires": 7200},
    },
    "collect-storage-metrics": {
        "task": "tasks.maintenance.collect_storage_metrics",
        "schedule": crontab(minute="10"),
        "options": {"queue": "maintenance_queue", "expires": 1800},
    },
    "archive-old-posts": {
        "task": "tasks.maintenance.archive_old_posts",
        "schedule": crontab(minute="45", hour="2"),
        "options": {"queue": "maintenance_queue", "expires": 7200},
    },
    
    # Weekly Discovery (Optional)
    "discover-new-communities-weekly": {
        "task": "tasks.discovery.discover_new_communities_weekly",
        "schedule": crontab(minute="0", hour="3", day_of_week="sun"),
        "options": {"queue": "probe_queue", "expires": 7200},
    },
    
    # Daily/Nightly Batch Jobs
    "comments-backfill-recent-full": {
        "task": "comments.backfill_recent_full_daily",
        "schedule": crontab(minute="10", hour="3"),
        "options": {"queue": "backfill_queue", "expires": 7200},
    },
    "subreddit-capture-snapshot": {
        "task": "subreddit.capture_snapshot_daily",
        "schedule": crontab(minute="5", hour="3"),
        "options": {"queue": "crawler_queue", "expires": 3600},
    },
    "posts-label-recent": {
        "task": "posts.label_recent",
        "schedule": crontab(minute="20", hour="2"),
        "options": {"queue": "maintenance_queue", "expires": 3600},
    },
    "generate-daily-tier-suggestions": {
        "task": "tasks.tier.generate_daily_suggestions",
        "schedule": crontab(minute="0", hour="1"),
        "options": {"queue": "monitoring_queue", "expires": 3600},
    },
    "emit-daily-tier-suggestion-decision-units": {
        "task": "tasks.tier.emit_daily_suggestion_decision_units",
        "schedule": crontab(minute="10", hour="1"),
        "options": {"queue": "monitoring_queue", "expires": 3600},
    },
    # Weekly recalibration of crawl frequencies
    "weekly-recalibration": {
        "task": "tasks.recalibrate_community_schedules",
        "schedule": crontab(day_of_week="mon", hour="4", minute="0"),
        "options": {"queue": "maintenance_queue", "expires": 7200},
    },
}

# Optional: embeddings backfill（默认开启；如需关闭设 EMBEDDING_BEAT_ENABLED=0）
if os.getenv("EMBEDDING_BEAT_ENABLED", "1") == "1":
    celery_app.conf.beat_schedule["embeddings-backfill-posts"] = {
        "task": "tasks.embedding.backfill_posts_batch",
        "schedule": crontab(minute="5", hour="*/1"),
        "options": {"queue": "maintenance_queue", "expires": 3600},
    }
    if os.getenv("EMBEDDING_COMMENTS_BEAT_ENABLED", "1") == "1":
        celery_app.conf.beat_schedule["embeddings-backfill-comments"] = {
            "task": "tasks.embedding.backfill_comments_batch",
            "schedule": crontab(minute="20", hour="*/1"),
            "options": {"queue": "maintenance_queue", "expires": 3600},
        }

# Optional: probe_hot 定时雷达（默认开启；如需关闭设 PROBE_HOT_BEAT_ENABLED=0）
if os.getenv("PROBE_HOT_BEAT_ENABLED", "1") == "1":
    celery_app.conf.beat_schedule["probe-hot-12h"] = {
        "task": "tasks.probe.run_hot_probe",
        "schedule": crontab(minute="15", hour="3,15"),
        "options": {"queue": "probe_queue", "expires": 7200},
    }

# Import ensures registration even when autodiscovery is executed in tooling
# contexts (e.g. verify_celery_config.py) where lazy loading might skip it.
try:
    from app.tasks import analysis_task as _analysis_task  # noqa: F401
    from app.tasks import crawler_task as _crawler_task  # noqa: F401
    from app.tasks import maintenance_task as _maintenance_task  # noqa: F401
    from app.tasks import monitoring_task as _monitoring_task  # noqa: F401
    from app.tasks import warmup_crawler as _warmup_crawler  # noqa: F401
    from app.tasks import metrics_task as _metrics_task  # noqa: F401
    from app.tasks import discovery_task as _discovery_task  # noqa: F401
    from app.tasks import semantic_task as _semantic_task  # noqa: F401
    from app.tasks import tier_intelligence_task as _tier_task  # noqa: F401
except Exception:  # pragma: no cover - defensive guard for diagnostics
    pass

_BOOTSTRAP_TASK_NAME = "tasks.crawler.crawl_seed_communities_incremental"
_BOOTSTRAP_FLAG_ATTR = "_auto_crawl_bootstrap_sent"
_BOOTSTRAP_DISABLE_ENV = "DISABLE_AUTO_CRAWL_BOOTSTRAP"


def trigger_auto_crawl_bootstrap(app: Celery | None = None) -> bool:
    """Trigger the first incremental crawl once workers are ready."""
    celery_instance = app or celery_app
    if os.getenv(_BOOTSTRAP_DISABLE_ENV) == "1":
        celery_instance.conf.auto_crawl_bootstrap_state = "disabled"
        return False
    if getattr(celery_instance, _BOOTSTRAP_FLAG_ATTR, False):
        return False
    try:
        celery_instance.send_task(_BOOTSTRAP_TASK_NAME)
    except Exception:  # pragma: no cover
        logging.getLogger(__name__).exception("Auto crawl bootstrap dispatch failed")
        celery_instance.conf.auto_crawl_bootstrap_state = "error"
        return False
    setattr(celery_instance, _BOOTSTRAP_FLAG_ATTR, True)
    celery_instance.conf.auto_crawl_bootstrap_state = "sent"
    return True


@worker_ready.connect  # type: ignore[misc]
def _handle_worker_ready(sender: Any = None, **_kwargs: Any) -> None:
    app_instance = getattr(sender, "app", None)
    trigger_auto_crawl_bootstrap(app_instance)

# Expose alias expected by `celery -A app.core.celery_app ...`.
app = celery_app

__all__ = ["celery_app", "app", "trigger_auto_crawl_bootstrap"]
