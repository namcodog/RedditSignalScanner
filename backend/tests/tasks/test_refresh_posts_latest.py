"""
验收 posts_latest 物化视图刷新任务：
1. 任务已加入 Celery Beat
2. 调度频率为每小时一次
3. 实现函数调用数据库函数并返回刷新行数
"""
from __future__ import annotations

import pytest
from celery.schedules import crontab  # type: ignore[import-untyped]

from app.core.celery_app import celery_app


def test_refresh_posts_latest_task_scheduled() -> None:
    """验收: 物化视图刷新任务存在且调度正确。"""
    schedule = celery_app.conf.beat_schedule
    assert "refresh-posts-latest" in schedule

    task = schedule["refresh-posts-latest"]
    assert task["task"] == "tasks.maintenance.refresh_posts_latest"

    task_schedule = task["schedule"]
    assert isinstance(task_schedule, crontab)
    # 每小时第 5 分钟刷新一次
    assert task_schedule.minute == {5}
    assert task_schedule.hour == set(range(24))

    options = task.get("options", {})
    assert options.get("queue") == "maintenance_queue"
    assert options.get("expires") == 1800


@pytest.mark.asyncio
async def test_refresh_posts_latest_impl_executes_function() -> None:
    """验收: 刷新函数能够执行并返回刷新行数。"""
    from app.tasks.maintenance_task import refresh_posts_latest_impl

    result = await refresh_posts_latest_impl()

    assert result["status"] == "completed"
    assert "refreshed_count" in result
    assert isinstance(result["refreshed_count"], int)
