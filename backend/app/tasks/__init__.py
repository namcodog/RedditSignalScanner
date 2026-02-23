"""
Celery task package exposing background jobs.

Importing this module ensures Celery discovers registered tasks.
"""

from __future__ import annotations

# 导入模块以触发 Celery 任务注册（autodiscover 会加载 app.tasks 包）
from . import (
    analysis_task,
    crawler_task,
    crawl_execute_task,
    backfill_task,
    probe_task,
    comments_task,
    ingest_task,
    semantic_task,
    monitoring_task,
    metrics_task,
    community_member_sync_task,
    maintenance_task,
    scheduler_task,
    scoring_task,
)

__all__ = [
    "analysis_task",
    "crawler_task",
    "crawl_execute_task",
    "backfill_task",
    "probe_task",
    "comments_task",
    "ingest_task",
    "semantic_task",
    "monitoring_task",
    "metrics_task",
    "community_member_sync_task",
    "maintenance_task",
    "scheduler_task",
    "scoring_task",
]
