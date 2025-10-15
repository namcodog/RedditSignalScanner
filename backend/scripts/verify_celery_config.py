#!/usr/bin/env python
"""
Celery 配置验证脚本（PRD/PRD-04-任务系统.md 对应产物）
- 检查队列路由配置
- 检查任务自动发现
- 检查 broker 连接
- 检查 result backend 连接
- 检查 Worker 并发/重试配置
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

import redis.asyncio as redis

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.celery_app import celery_app  # noqa: E402

EXPECTED_TASK = "tasks.analysis.run"
EXPECTED_QUEUE = "analysis_queue"


async def _ping_redis(url: str) -> None:
    client = redis.from_url(url)
    try:
        await client.ping()
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()
        else:  # pragma: no cover - fallback for older redis versions
            await client.close()


def _assert_queue_routing(routes: Dict[str, Dict[str, str]]) -> None:
    route = routes.get(EXPECTED_TASK, {})
    queue = route.get("queue")
    if queue != EXPECTED_QUEUE:
        raise RuntimeError(
            f"Queue routing mismatch: expected {EXPECTED_TASK} → {EXPECTED_QUEUE}, got {queue!r}",
        )
    print(f"✅ Queue routing: {EXPECTED_TASK} → {EXPECTED_QUEUE}")


def _assert_task_autodiscovery() -> None:
    if importlib.util.find_spec("app.tasks") is None:
        raise RuntimeError("Task package 'app.tasks' not importable.")
    if EXPECTED_TASK not in celery_app.tasks:
        registered = ", ".join(sorted(celery_app.tasks.keys()))
        raise RuntimeError(f"Task '{EXPECTED_TASK}' not registered. Registered tasks: {registered}")
    print("✅ Task autodiscovery: app.tasks found")


def _assert_worker_config() -> None:
    concurrency = celery_app.conf.worker_concurrency
    max_retries = celery_app.conf.task_max_retries
    if concurrency is None or concurrency < 1:
        raise RuntimeError(f"Invalid worker concurrency value: {concurrency!r}")
    if max_retries is None or max_retries < 1:
        raise RuntimeError(f"Invalid task_max_retries value: {max_retries!r}")
    print(f"✅ Worker config: concurrency={concurrency}, max_retries={max_retries}")


def _ensure_redis_url(url: str, label: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise RuntimeError(f"{label} URL must use redis scheme, got {url!r}")


def main() -> int:
    routes: Dict[str, Dict[str, str]] = celery_app.conf.task_routes or {}
    try:
        _assert_queue_routing(routes)
        _assert_task_autodiscovery()
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    broker_url = celery_app.conf.broker_url
    result_backend = celery_app.conf.result_backend

    try:
        _ensure_redis_url(broker_url, "Broker")
        asyncio.run(_ping_redis(broker_url))
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"❌ Broker connection failed: {exc}")
        return 1
    else:
        print("✅ Broker connection: OK")

    try:
        _ensure_redis_url(result_backend, "Result backend")
        asyncio.run(_ping_redis(result_backend))
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"❌ Result backend connection failed: {exc}")
        return 1
    else:
        print("✅ Result backend: OK")

    try:
        _assert_worker_config()
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
