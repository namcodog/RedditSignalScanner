"""
测试 posts_hot 清理任务

验收标准:
1. 清理任务存在于 Beat schedule
2. 清理逻辑正确删除过期数据
3. 保留未过期数据
4. 执行耗时 <10秒
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.models.posts_storage import PostHot
from app.db.session import SessionFactory


class TestCleanupPostsHotTask:
    """测试 posts_hot 清理任务配置"""

    def test_cleanup_task_exists(self) -> None:
        """验收: 清理任务存在于 Beat schedule"""
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-expired-posts-hot" in schedule
        
        task = schedule["cleanup-expired-posts-hot"]
        assert task["task"] == "tasks.maintenance.cleanup_expired_posts_hot"
        
        # 验证调度频率（每6小时）
        from celery.schedules import crontab
        assert isinstance(task["schedule"], crontab)
        # crontab(hour="*/6") 表示 0, 6, 12, 18
        assert task["schedule"].hour == {0, 6, 12, 18}
        
        # 验证任务队列
        assert task.get("options", {}).get("queue") == "cleanup_queue"

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_posts(self) -> None:
        """验收: 清理逻辑正确删除过期数据"""
        async with SessionFactory() as db:
            # 准备测试数据: 插入过期和未过期的帖子
            now = datetime.now(timezone.utc)
            expired_time = now - timedelta(hours=25)  # 25小时前过期
            valid_time = now + timedelta(hours=23)    # 23小时后过期
            
            # 插入过期帖子
            expired_post = PostHot(
                source="reddit",
                source_post_id="test_expired_1",
                created_at=now - timedelta(days=2),
                cached_at=now - timedelta(days=2),
                expires_at=expired_time,
                title="Expired Post",
                body="This should be deleted",
                subreddit="test",
                score=10,
                num_comments=5,
            )
            db.add(expired_post)
            
            # 插入未过期帖子
            valid_post = PostHot(
                source="reddit",
                source_post_id="test_valid_1",
                created_at=now - timedelta(hours=1),
                cached_at=now - timedelta(hours=1),
                expires_at=valid_time,
                title="Valid Post",
                body="This should be kept",
                subreddit="test",
                score=20,
                num_comments=10,
            )
            db.add(valid_post)
            await db.commit()
            
            # 执行清理（导入清理函数）
            from app.tasks.maintenance_task import cleanup_expired_posts_hot_impl
            result = await cleanup_expired_posts_hot_impl()
            
            # 验证: 过期帖子已删除
            expired_count = await db.scalar(
                select(PostHot).where(PostHot.source_post_id == "test_expired_1")
            )
            assert expired_count is None
            
            # 验证: 未过期帖子保留
            valid_count = await db.scalar(
                select(PostHot).where(PostHot.source_post_id == "test_valid_1")
            )
            assert valid_count is not None
            
            # 验证返回值
            assert result["deleted_count"] >= 1
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cleanup_preserves_valid_posts(self) -> None:
        """验收: 保留未过期数据"""
        async with SessionFactory() as db:
            # 统计清理前的未过期帖子数
            before_count = await db.scalar(
                select(PostHot).where(PostHot.expires_at >= datetime.now(timezone.utc))
            )
            
            # 执行清理
            from app.tasks.maintenance_task import cleanup_expired_posts_hot_impl
            await cleanup_expired_posts_hot_impl()
            
            # 统计清理后的未过期帖子数
            after_count = await db.scalar(
                select(PostHot).where(PostHot.expires_at >= datetime.now(timezone.utc))
            )
            
            # 验证: 未过期帖子数量不变
            assert before_count == after_count

    @pytest.mark.asyncio
    async def test_cleanup_performance(self) -> None:
        """验收: 执行耗时 <10秒"""
        import time
        
        start_time = time.time()
        
        from app.tasks.maintenance_task import cleanup_expired_posts_hot_impl
        result = await cleanup_expired_posts_hot_impl()
        
        duration = time.time() - start_time
        
        # 验证: 执行耗时 <10秒
        assert duration < 10.0
        
        # 验证: 返回值包含 duration
        assert "duration_seconds" in result
        assert result["duration_seconds"] < 10.0

