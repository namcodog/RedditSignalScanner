from __future__ import annotations

import sys
from pathlib import Path

import pytest
import redis

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_celery_app_configured() -> None:
    """验证 Celery app 配置正确。"""
    from app.core.celery_app import celery_app

    assert celery_app.conf.broker_url
    assert celery_app.conf.result_backend


def test_celery_task_registered() -> None:
    """验证分析任务已注册。"""
    from app.core.celery_app import celery_app

    assert "tasks.analysis.run" in celery_app.tasks


def test_redis_connection() -> None:
    """验证 Redis 连接可用。"""
    from app.core.celery_app import celery_app

    client = redis.Redis.from_url(celery_app.conf.broker_url)
    try:
        assert client.ping()
    except redis.exceptions.RedisError as exc:
        pytest.skip(f"Redis not available at {celery_app.conf.broker_url}: {exc}")
    finally:
        client.close()
