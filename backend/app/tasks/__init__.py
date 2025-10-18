"""
Celery task package exposing background jobs.

Importing this module ensures Celery discovers registered tasks.
"""

from __future__ import annotations

from .analysis_task import run_analysis_task
from .crawler_task import crawl_community, crawl_seed_communities
from .monitoring_task import (
    monitor_api_calls,
    monitor_cache_health,
    monitor_crawler_health,
)

__all__ = [
    "run_analysis_task",
    "crawl_community",
    "crawl_seed_communities",
    "monitor_api_calls",
    "monitor_cache_health",
    "monitor_crawler_health",
]
