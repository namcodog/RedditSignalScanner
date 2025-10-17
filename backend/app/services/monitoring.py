from __future__ import annotations

from typing import Any, Dict, Mapping

from celery import Celery  # type: ignore[import-untyped]
from redis import Redis


class MonitoringService:
    """Collect operational metrics for Admin dashboard reporting."""

    def __init__(self, redis_client: Redis, celery_app: Celery):  # type: ignore[type-arg]
        self._redis = redis_client
        self._celery = celery_app

    def get_celery_stats(self) -> Dict[str, int]:
        """Return aggregate Celery worker statistics."""

        inspect = self._celery.control.inspect()
        if inspect is None:
            return {
                "active_workers": 0,
                "active_tasks": 0,
                "reserved_tasks": 0,
                "scheduled_tasks": 0,
                "queued_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
            }

        stats = inspect.stats() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}

        active_workers = len(stats) if isinstance(stats, dict) else 0
        active_tasks = sum(len(tasks) for tasks in active.values())
        reserved_tasks = sum(len(tasks) for tasks in reserved.values())
        scheduled_tasks = sum(len(tasks) for tasks in scheduled.values())

        completed_tasks = 0
        failed_tasks = 0
        if isinstance(stats, dict):
            for worker_stats in stats.values():
                totals = worker_stats.get("total")
                if isinstance(totals, dict):
                    completed_tasks += sum(totals.values())
                elif isinstance(totals, int):
                    completed_tasks += totals

                failed = worker_stats.get("failed")
                if isinstance(failed, int):
                    failed_tasks += failed

        return {
            "active_workers": active_workers,
            "active_tasks": active_tasks,
            "reserved_tasks": reserved_tasks,
            "scheduled_tasks": scheduled_tasks,
            "queued_tasks": reserved_tasks + scheduled_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
        }

    def get_redis_stats(self) -> Dict[str, float]:
        """Return Redis server statistics required by the admin dashboard."""

        info_raw = self._redis.info()  # type: ignore[misc]
        info: Dict[str, Any] = dict(info_raw) if isinstance(info_raw, dict) else {}
        hits = int(info.get("keyspace_hits", 0))
        misses = int(info.get("keyspace_misses", 0))
        total_requests = hits + misses
        hit_rate = (hits / total_requests) if total_requests else 1.0

        used_memory_mb = float(info.get("used_memory", 0)) / (1024 * 1024)

        return {
            "connected_clients": int(info.get("connected_clients", 0)),
            "used_memory_mb": round(used_memory_mb, 2),
            "hit_rate": round(hit_rate, 4),
            "uptime_seconds": int(info.get("uptime_in_seconds", 0)),
            "ops_per_sec": int(info.get("instantaneous_ops_per_sec", 0)),
        }


__all__ = ["MonitoringService"]
