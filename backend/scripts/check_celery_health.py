"""
Celery health verification script used by Day 6 operational checklist.

The script validates:
1. Celery workers are reachable.
2. Queue pressure stays below configured thresholds.
3. Failure rate remains within acceptable limits.
4. The Redis-backed task status cache responds after transient outages.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.core.celery_app import celery_app
from app.services.task_status_cache import TaskStatusCache


class CeleryHealthError(RuntimeError):
    """Raised when Celery health checks fail."""


async def _ensure_status_cache_ready(retries: int = 3, delay_seconds: float = 1.0) -> None:
    cache = TaskStatusCache()
    try:
        for attempt in range(retries):
            try:
                await cache.redis.ping()
            except Exception as exc:
                if attempt == retries - 1:
                    raise CeleryHealthError("Redis status cache is unavailable") from exc
                await asyncio.sleep(delay_seconds)
            else:
                return
    finally:
        try:
            await cache.redis.close()
        except Exception:
            pass


async def check_celery_health(
    *,
    max_reserved_tasks: int = 100,
    max_failure_rate: float = 0.05,
) -> Dict[str, int]:
    inspect = celery_app.control.inspect()
    if inspect is None:
        raise CeleryHealthError("Unable to contact Celery control interface")

    active_workers = inspect.active() or {}
    reserved_tasks = inspect.reserved() or {}
    scheduled_tasks = inspect.scheduled() or {}

    # Phase106（大白话）：
    # 本地/开发环境里 inspect.*() 偶发超时会直接返回空 dict，导致“worker 明明在线”却被判死。
    # 兜底：当 inspect 三件套都空时，用 ping 只判断“有没有 worker 活着”。
    worker_names = set(active_workers) | set(reserved_tasks) | set(scheduled_tasks)
    if not worker_names:
        try:
            replies = celery_app.control.ping(timeout=3) or []
        except Exception:
            replies = []
        for item in replies:
            if isinstance(item, dict):
                for name in item.keys():
                    if isinstance(name, str) and name.strip():
                        worker_names.add(name.strip())

    if not worker_names:
        raise CeleryHealthError("No active Celery workers detected")

    total_active_tasks = sum(len(tasks) for tasks in active_workers.values())
    total_reserved_tasks = sum(len(tasks) for tasks in reserved_tasks.values())
    total_scheduled_tasks = sum(len(tasks) for tasks in scheduled_tasks.values())

    if total_reserved_tasks > max_reserved_tasks:
        raise CeleryHealthError(
            f"Reserved task backlog too high: {total_reserved_tasks} > {max_reserved_tasks}"
        )

    stats = inspect.stats() or {}
    total_tasks = 0
    total_failures = 0
    for worker_stats in stats.values():
        totals = worker_stats.get("total", {})
        failures = worker_stats.get("failures", {})
        total_tasks += sum(totals.values())
        total_failures += sum(failures.values())

    if total_tasks and (total_failures / total_tasks) > max_failure_rate:
        raise CeleryHealthError("Celery failure rate exceeds threshold")

    await _ensure_status_cache_ready()

    return {
        "active_workers": len(worker_names),
        "active_tasks": total_active_tasks,
        "reserved_tasks": total_reserved_tasks,
        "scheduled_tasks": total_scheduled_tasks,
        "total_tasks": total_active_tasks + total_reserved_tasks + total_scheduled_tasks,
    }


def main() -> None:
    try:
        summary = asyncio.run(check_celery_health())
    except CeleryHealthError as exc:
        raise SystemExit(f"[celery-health] FAILED: {exc}") from exc

    print("[celery-health] OK", summary)


if __name__ == "__main__":
    main()
