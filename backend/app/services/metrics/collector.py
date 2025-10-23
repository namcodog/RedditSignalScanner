"""
Quality Metrics Collector

基于 speckit-006 User Story 1 (US1) - Task T006
从数据库统计采集成功率、重复率、处理耗时，并保存到数据库和文件
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl_metrics import CrawlMetrics
from app.models.metrics import QualityMetrics
from app.models.task import Task, TaskStatus


async def collect_metrics(
    db: AsyncSession,
    target_date: Optional[date] = None,
) -> QualityMetrics:
    """从数据库统计质量指标
    
    Args:
        db: 数据库会话
        target_date: 目标日期（默认为昨天）
    
    Returns:
        QualityMetrics: 质量指标对象
    
    Raises:
        ValueError: 如果没有找到数据
    """
    # 默认统计昨天的数据
    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    
    # 1. 从 CrawlMetrics 获取采集成功率和重复率
    crawl_query = select(
        func.sum(CrawlMetrics.successful_crawls).label("successful"),
        func.sum(CrawlMetrics.failed_crawls).label("failed"),
        func.sum(CrawlMetrics.total_duplicates).label("duplicates"),
        func.sum(CrawlMetrics.total_new_posts).label("new_posts"),
    ).where(CrawlMetrics.metric_date == target_date)
    
    crawl_result = await db.execute(crawl_query)
    crawl_row = crawl_result.first()
    
    if not crawl_row or crawl_row.successful is None:
        raise ValueError(f"No crawl metrics found for date {target_date}")
    
    # 计算采集成功率
    total_crawls = (crawl_row.successful or 0) + (crawl_row.failed or 0)
    collection_success_rate = (
        Decimal(str(round((crawl_row.successful or 0) / total_crawls, 4)))
        if total_crawls > 0
        else Decimal("0.0000")
    )
    
    # 计算重复率
    total_posts = (crawl_row.new_posts or 0) + (crawl_row.duplicates or 0)
    deduplication_rate = (
        Decimal(str(round((crawl_row.duplicates or 0) / total_posts, 4)))
        if total_posts > 0
        else Decimal("0.0000")
    )
    
    # 2. 从 Task 获取处理耗时 P50/P95
    # 查询当天完成的任务
    day_start = datetime.combine(target_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    day_end = day_start + timedelta(days=1)
    
    processing_query = select(
        func.percentile_cont(0.5).within_group(
            func.extract("epoch", Task.completed_at - Task.started_at)
        ).label("p50"),
        func.percentile_cont(0.95).within_group(
            func.extract("epoch", Task.completed_at - Task.started_at)
        ).label("p95"),
    ).where(
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at.is_not(None),
        Task.started_at.is_not(None),
        Task.completed_at >= day_start,
        Task.completed_at < day_end,
    )
    
    processing_result = await db.execute(processing_query)
    processing_row = processing_result.first()
    
    # 如果当天没有完成的任务，使用默认值 0
    processing_time_p50 = (
        Decimal(str(round(float(processing_row.p50 or 0.0), 2)))
        if processing_row and processing_row.p50
        else Decimal("0.00")
    )
    processing_time_p95 = (
        Decimal(str(round(float(processing_row.p95 or 0.0), 2)))
        if processing_row and processing_row.p95
        else Decimal("0.00")
    )
    
    # 3. 创建 QualityMetrics 对象
    metrics = QualityMetrics(
        date=target_date,
        collection_success_rate=collection_success_rate,
        deduplication_rate=deduplication_rate,
        processing_time_p50=processing_time_p50,
        processing_time_p95=processing_time_p95,
    )
    
    return metrics


async def save_metrics(
    db: AsyncSession,
    metrics: QualityMetrics,
    output_dir: Path = Path("reports/daily_metrics"),
) -> Path:
    """保存质量指标到数据库和文件

    Args:
        db: 数据库会话
        metrics: 质量指标对象
        output_dir: 输出目录

    Returns:
        Path: 保存的文件路径
    """
    # 1. 保存到数据库（如果已存在则更新）
    existing = await db.execute(
        select(QualityMetrics).where(QualityMetrics.date == metrics.date)
    )
    existing_metrics = existing.scalar_one_or_none()

    # 用于后续写文件时取到有效的 created_at
    persisted: QualityMetrics

    if existing_metrics:
        # 更新现有记录
        existing_metrics.collection_success_rate = metrics.collection_success_rate
        existing_metrics.deduplication_rate = metrics.deduplication_rate
        existing_metrics.processing_time_p50 = metrics.processing_time_p50
        existing_metrics.processing_time_p95 = metrics.processing_time_p95
        existing_metrics.created_at = datetime.now(timezone.utc)
        persisted = existing_metrics
    else:
        # 插入新记录
        db.add(metrics)
        persisted = metrics

    await db.commit()

    # 确保新插入记录拥有 created_at（由数据库默认值/ORM 默认填充）
    try:
        await db.refresh(persisted)
    except Exception:
        # 在部分后端驱动下 refresh 不是必须的，忽略刷新失败
        pass

    # 2. 保存到 JSONL 文件
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "daily_metrics.jsonl"

    # 准备 JSON 数据（使用已持久化实例）
    metrics_dict = {
        "date": persisted.date.isoformat(),
        "collection_success_rate": float(persisted.collection_success_rate),
        "deduplication_rate": float(persisted.deduplication_rate),
        "processing_time_p50": float(persisted.processing_time_p50),
        "processing_time_p95": float(persisted.processing_time_p95),
        "created_at": (persisted.created_at or datetime.now(timezone.utc)).isoformat(),
    }

    # 追加到 JSONL 文件
    with output_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(metrics_dict, ensure_ascii=False) + "\n")

    return output_file


__all__ = ["collect_metrics", "save_metrics"]

