#!/usr/bin/env python
"""
Celery Worker 启动脚本（PRD/PRD-04-任务系统.md 对应产物）
- 验证 Redis 连接
- 验证 PostgreSQL 连接
- 启动 Worker 进程
- 配置日志级别
- 配置并发数
"""

from __future__ import annotations

import argparse
import asyncio
import multiprocessing
import os
import sys
import socket
import time
from importlib import import_module
from pathlib import Path
from typing import Optional, cast

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.celery_app import celery_app  # noqa: E402

SESSION_MODULE = import_module("app.db.session")
DEFAULT_DATABASE_URL = cast(str, getattr(SESSION_MODULE, "DATABASE_URL", ""))

DEFAULT_QUEUE = "analysis_queue"


def _resolve_required_value(name: str, fallback: Optional[str]) -> str:
    value = os.getenv(name) or (fallback or "")
    if not value:
        raise RuntimeError(f"Missing required configuration for {name}.")
    return value


async def _verify_redis_connection(url: str) -> None:
    client = redis.from_url(url)
    try:
        await client.ping()
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()
        else:  # pragma: no cover - fallback for older redis versions
            await client.close()


async def _verify_database_connection(url: str) -> None:
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


def _default_concurrency() -> int:
    configured = os.getenv("CELERY_WORKER_COUNT")
    if configured:
        try:
            as_int = int(configured)
            if as_int > 0:
                return as_int
        except ValueError:
            pass

    try:
        cpu_count = multiprocessing.cpu_count()
    except NotImplementedError:
        cpu_count = 1

    return max(1, min(cpu_count, 4))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="启动 Celery Worker（analysis_queue）。",
    )
    parser.add_argument("--loglevel", default="info", help="Worker 日志级别，默认 info")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Worker 并发数；默认取 min(cpu_cores, 4)",
    )
    parser.add_argument(
        "--queue",
        default=DEFAULT_QUEUE,
        help="队列名称，默认 analysis_queue",
    )
    parser.add_argument(
        "--hostname",
        default=None,
        help="Worker host name，默认自动附带主机名与进程号",
    )
    args = parser.parse_args()

    try:
        broker_url = _resolve_required_value("CELERY_BROKER_URL", celery_app.conf.broker_url)
        database_url = _resolve_required_value("DATABASE_URL", DEFAULT_DATABASE_URL or None)
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    try:
        asyncio.run(_verify_redis_connection(broker_url))
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"❌ Redis connection failed: {exc}")
        return 1
    else:
        print("✅ Redis connection verified")

    try:
        asyncio.run(_verify_database_connection(database_url))
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"❌ Database connection failed: {exc}")
        return 1
    else:
        print("✅ Database connection verified")

    queue = args.queue or DEFAULT_QUEUE
    concurrency = args.concurrency or celery_app.conf.worker_concurrency or _default_concurrency()
    loglevel = args.loglevel or "info"
    hostname = (
        args.hostname
        or os.getenv("CELERY_WORKER_HOSTNAME")
        or f"analysis@{socket.gethostname()}-{os.getpid()}-{int(time.time())}"
    )

    celery_args = [
        "worker",
        f"--loglevel={loglevel}",
        f"--queues={queue}",
        f"--concurrency={concurrency}",
        f"--hostname={hostname}",
    ]

    print("✅ Starting Celery worker...")
    celery_app.worker_main(celery_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
