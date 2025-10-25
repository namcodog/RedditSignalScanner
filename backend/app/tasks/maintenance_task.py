"""
维护任务：数据库清理、备份等

包含:
- refresh_posts_latest: 刷新 posts_latest 物化视图
- cleanup_expired_posts_hot: 清理过期的 posts_hot 数据
- cleanup_old_posts: 清理超过保留期的 posts_raw 冷数据
- collect_storage_metrics: 采集存储层指标快照
- archive_old_posts: 将历史版本归档至 posts_archive
- check_storage_capacity: 检查数据库容量并预警
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.db.session import SessionFactory

logger = get_task_logger(__name__)
_MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_STORAGE_CAPACITY_THRESHOLD_GB = float(
    os.getenv("STORAGE_CAPACITY_THRESHOLD_GB", "50")
)

async def refresh_posts_latest_impl() -> dict[str, Any]:
    """
    刷新 posts_latest 物化视图的实现函数。
    """
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        result = await db.execute(
            text("SELECT refresh_posts_latest() AS refreshed_count")
        )
        refreshed_count = int(result.scalar() or 0)
        await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    _MODULE_LOGGER.info(
        "🔄 posts_latest 物化视图刷新完成: count=%s, duration=%.2fs",
        refreshed_count,
        duration,
    )
    return {
        "status": "completed",
        "refreshed_count": refreshed_count,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.refresh_posts_latest")  # type: ignore[misc]
def refresh_posts_latest() -> dict[str, Any]:
    """
    Celery 任务：刷新 posts_latest 物化视图。
    """
    import asyncio

    logger.info("🔄 开始执行 posts_latest 物化视图刷新任务")
    result = asyncio.run(refresh_posts_latest_impl())
    logger.info("✅ 物化视图刷新任务完成: %s", result)
    return result


async def cleanup_expired_posts_hot_impl() -> dict[str, Any]:
    """
    清理过期的 posts_hot 数据（实现函数）。
    """
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        result = await db.execute(
            text("SELECT cleanup_expired_hot_cache() AS deleted_count")
        )
        await db.commit()

    deleted_count = int(result.scalar() or 0)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    _MODULE_LOGGER.info(
        "🧹 posts_hot 清理完成: deleted=%s, duration=%.2fs",
        deleted_count,
        duration,
    )

    return {
        "status": "completed",
        "deleted_count": deleted_count,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_expired_posts_hot")  # type: ignore[misc]
def cleanup_expired_posts_hot() -> dict[str, Any]:
    """
    Celery 任务: 清理过期的 posts_hot 数据。
    """
    import asyncio
    
    logger.info("🧹 开始执行 posts_hot 清理任务")
    result = asyncio.run(cleanup_expired_posts_hot_impl())
    logger.info(f"✅ 清理任务完成: {result}")
    
    return result


async def collect_storage_metrics_impl() -> dict[str, Any]:
    """采集并写入 storage_metrics 表的实现函数。"""
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        metrics_result = await db.execute(text("SELECT metric, value FROM get_storage_stats()"))
        stats = {row.metric: int(row.value) for row in metrics_result}

        posts_raw_total = stats.get("posts_raw_total", 0)
        posts_raw_current = stats.get("posts_raw_current", 0)
        posts_hot_total = stats.get("posts_hot_total", 0)
        posts_hot_expired = stats.get("posts_hot_expired", 0)
        unique_subreddits = stats.get("unique_subreddits", 0)
        total_versions = stats.get("total_versions", 0)

        duplicates = posts_raw_total - posts_raw_current
        dedup_rate = duplicates / posts_raw_total if posts_raw_total else 0.0

        insert_result = await db.execute(
            text(
                """
                INSERT INTO storage_metrics (
                    posts_raw_total,
                    posts_raw_current,
                    posts_hot_total,
                    posts_hot_expired,
                    unique_subreddits,
                    total_versions,
                    dedup_rate
                )
                VALUES (
                    :posts_raw_total,
                    :posts_raw_current,
                    :posts_hot_total,
                    :posts_hot_expired,
                    :unique_subreddits,
                    :total_versions,
                    :dedup_rate
                )
                RETURNING id, collected_at
                """
            ),
            {
                "posts_raw_total": posts_raw_total,
                "posts_raw_current": posts_raw_current,
                "posts_hot_total": posts_hot_total,
                "posts_hot_expired": posts_hot_expired,
                "unique_subreddits": unique_subreddits,
                "total_versions": total_versions,
                "dedup_rate": round(dedup_rate, 6),
            },
        )
        inserted = insert_result.one()
        await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    snapshot = {
        "status": "completed",
        "id": int(inserted.id),
        "collected_at": inserted.collected_at.isoformat(),
        "posts_raw_total": posts_raw_total,
        "posts_raw_current": posts_raw_current,
        "posts_hot_total": posts_hot_total,
        "posts_hot_expired": posts_hot_expired,
        "unique_subreddits": unique_subreddits,
        "total_versions": total_versions,
        "dedup_rate": round(dedup_rate, 6),
        "duration_seconds": duration,
    }
    _MODULE_LOGGER.info("📊 存储指标采集完成: %s", snapshot)
    return snapshot


@celery_app.task(name="tasks.maintenance.collect_storage_metrics")  # type: ignore[misc]
def collect_storage_metrics() -> dict[str, Any]:
    """Celery 任务：采集存储层质量指标。"""
    import asyncio

    logger.info("📊 开始采集存储层指标")
    result = asyncio.run(collect_storage_metrics_impl())
    logger.info("✅ 存储层指标采集完成: %s", result)
    return result


async def cleanup_old_posts_impl(retention_days: int = 90) -> dict[str, Any]:
    """
    清理 posts_raw 中超过保留期的历史数据。
    """
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        result = await db.execute(
            text("SELECT cleanup_old_posts(:retention_days) AS deleted_count"),
            {"retention_days": retention_days},
        )
        await db.commit()

    deleted_count = int(result.scalar() or 0)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    _MODULE_LOGGER.info(
        "🧊 posts_raw 冷库清理完成: retention=%s, deleted=%s, duration=%.2fs",
        retention_days,
        deleted_count,
        duration,
    )

    return {
        "status": "completed",
        "retention_days": retention_days,
        "deleted_count": deleted_count,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_old_posts")  # type: ignore[misc]
def cleanup_old_posts(retention_days: int = 90) -> dict[str, Any]:
    """
    Celery 任务：清理超过保留期的 posts_raw 冷数据。
    """
    import asyncio

    logger.info("🧊 开始执行 posts_raw 冷库清理任务 (retention=%s 天)", retention_days)
    result = asyncio.run(cleanup_old_posts_impl(retention_days=retention_days))
    logger.info("✅ 冷库清理任务完成: %s", result)
    return result


async def archive_old_posts_impl(
    retention_days: int = 90, batch_size: int = 1000
) -> dict[str, Any]:
    """将历史版本归档至 posts_archive。"""
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        result = await db.execute(
            text(
                "SELECT archive_old_posts(:retention_days, :batch_size) AS archived_count"
            ),
            {"retention_days": retention_days, "batch_size": batch_size},
        )
        await db.commit()

    archived_count = int(result.scalar() or 0)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {
        "status": "completed",
        "retention_days": retention_days,
        "batch_size": batch_size,
        "archived_count": archived_count,
        "duration_seconds": duration,
    }
    _MODULE_LOGGER.info("🗄️ 归档任务完成: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.archive_old_posts")  # type: ignore[misc]
def archive_old_posts(retention_days: int = 90, batch_size: int = 1000) -> dict[str, Any]:
    """Celery 任务：归档历史版本数据。"""
    import asyncio

    logger.info(
        "🗄️ 开始执行 posts_raw 归档任务 (retention=%s, batch=%s)",
        retention_days,
        batch_size,
    )
    result = asyncio.run(
        archive_old_posts_impl(retention_days=retention_days, batch_size=batch_size)
    )
    logger.info("✅ 归档任务完成: %s", result)
    return result


async def check_storage_capacity_impl(
    threshold_gb: float | None = None,
) -> dict[str, Any]:
    """检查数据库容量并返回评估结果。"""
    threshold = (
        threshold_gb
        if threshold_gb is not None
        else DEFAULT_STORAGE_CAPACITY_THRESHOLD_GB
    )

    async with SessionFactory() as db:
        result = await db.execute(
            text(
                """
                SELECT
                    pg_database_size(current_database()) AS database_size,
                    pg_total_relation_size('posts_raw'::regclass) AS posts_raw_size,
                    pg_total_relation_size('posts_hot'::regclass) AS posts_hot_size
                """
            )
        )
        row = result.one()

    database_size_gb = row.database_size / 1024**3
    posts_raw_size_gb = row.posts_raw_size / 1024**3
    posts_hot_size_gb = row.posts_hot_size / 1024**3
    above_threshold = database_size_gb >= threshold

    payload = {
        "status": "alert" if above_threshold else "ok",
        "database_size_gb": round(database_size_gb, 3),
        "posts_raw_size_gb": round(posts_raw_size_gb, 3),
        "posts_hot_size_gb": round(posts_hot_size_gb, 3),
        "threshold_gb": threshold,
    }

    if above_threshold:
        _MODULE_LOGGER.warning("⚠️ 数据库容量接近阈值: %s", payload)
    else:
        _MODULE_LOGGER.info("📦 数据库容量检查通过: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.check_storage_capacity")  # type: ignore[misc]
def check_storage_capacity(threshold_gb: float | None = None) -> dict[str, Any]:
    """Celery 任务：检查数据库容量并输出预警。"""
    import asyncio

    result = asyncio.run(check_storage_capacity_impl(threshold_gb=threshold_gb))
    logger.info("📦 存储容量检查结果: %s", result)
    return result
