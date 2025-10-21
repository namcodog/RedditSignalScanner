"""
维护任务：数据库清理、备份等

包含:
- cleanup_expired_posts_hot: 清理过期的 posts_hot 数据
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import delete, select

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.models.posts_storage import PostHot

logger = get_task_logger(__name__)
_MODULE_LOGGER = logging.getLogger(__name__)


async def cleanup_expired_posts_hot_impl() -> dict[str, Any]:
    """
    清理过期的 posts_hot 数据（实现函数）
    
    删除 expires_at < NOW() 的记录
    
    Returns:
        {
            "status": "completed",
            "deleted_count": int,
            "duration_seconds": float,
        }
    """
    start_time = datetime.now(timezone.utc)
    
    async with SessionFactory() as db:
        # 统计过期数据
        expired_count_result = await db.execute(
            select(PostHot).where(PostHot.expires_at < datetime.now(timezone.utc))
        )
        expired_count = len(expired_count_result.all())
        
        _MODULE_LOGGER.info(f"🧹 开始清理过期 posts_hot 数据，预计删除 {expired_count} 条")
        
        # 删除过期数据
        stmt = delete(PostHot).where(PostHot.expires_at < datetime.now(timezone.utc))
        result = await db.execute(stmt)
        await db.commit()
        
        deleted_count = result.rowcount
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        _MODULE_LOGGER.info(
            f"✅ 清理完成: 删除 {deleted_count} 条过期数据，耗时 {duration:.2f}s"
        )
        
        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "duration_seconds": duration,
        }


@celery_app.task(name="tasks.maintenance.cleanup_expired_posts_hot")  # type: ignore[misc]
def cleanup_expired_posts_hot() -> dict[str, Any]:
    """
    Celery 任务: 清理过期的 posts_hot 数据

    调度: 每6小时执行一次
    队列: cleanup_queue
    """
    import asyncio
    
    logger.info("🧹 开始执行 posts_hot 清理任务")
    result = asyncio.run(cleanup_expired_posts_hot_impl())
    logger.info(f"✅ 清理任务完成: {result}")
    
    return result

