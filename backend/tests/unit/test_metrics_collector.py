"""
Unit tests for metrics collector

基于 speckit-006 User Story 1 (US1) - Task T006
"""
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.crawl_metrics import CrawlMetrics
from app.models.metrics import QualityMetrics
from app.models.task import Task, TaskStatus
from app.services.metrics.collector import collect_metrics, save_metrics


@pytest.mark.asyncio
async def test_collect_metrics_success(db_session, test_user):
    """测试成功采集质量指标"""
    target_date = date(2025, 10, 21)
    
    # 准备测试数据：CrawlMetrics
    crawl_metric = CrawlMetrics(
        metric_date=target_date,
        metric_hour=12,
        successful_crawls=98,
        failed_crawls=2,
        total_new_posts=900,
        total_duplicates=100,
        cache_hit_rate=Decimal("0.90"),
        valid_posts_24h=1000,
        total_communities=200,
        empty_crawls=0,
        avg_latency_seconds=Decimal("1.5"),
    )
    db_session.add(crawl_metric)
    
    # 准备测试数据：Task
    day_start = datetime.combine(target_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    
    task1 = Task(
        user_id=test_user.id,
        product_description="Test product 1",
        status=TaskStatus.COMPLETED,
        started_at=day_start,
        completed_at=day_start + timedelta(seconds=18),  # 18 秒
    )
    task2 = Task(
        user_id=test_user.id,
        product_description="Test product 2",
        status=TaskStatus.COMPLETED,
        started_at=day_start + timedelta(hours=1),
        completed_at=day_start + timedelta(hours=1, seconds=45),  # 45 秒
    )
    db_session.add_all([task1, task2])
    await db_session.commit()
    
    # 执行采集
    metrics = await collect_metrics(db_session, target_date)
    
    # 验证结果
    assert metrics.date == target_date
    assert metrics.collection_success_rate == Decimal("0.9800")  # 98/100
    assert metrics.deduplication_rate == Decimal("0.1000")  # 100/1000
    assert metrics.processing_time_p50 > 0  # P50 应该在 18-45 之间
    assert metrics.processing_time_p95 > 0  # P95 应该接近 45


@pytest.mark.asyncio
async def test_collect_metrics_no_data(db_session):
    """测试没有数据时抛出异常"""
    target_date = date(2025, 10, 21)
    
    with pytest.raises(ValueError, match="No crawl metrics found"):
        await collect_metrics(db_session, target_date)


@pytest.mark.asyncio
async def test_collect_metrics_no_tasks(db_session):
    """测试没有任务时使用默认值"""
    target_date = date(2025, 10, 21)
    
    # 只准备 CrawlMetrics，不准备 Task
    crawl_metric = CrawlMetrics(
        metric_date=target_date,
        metric_hour=12,
        successful_crawls=100,
        failed_crawls=0,
        total_new_posts=1000,
        total_duplicates=0,
        cache_hit_rate=Decimal("0.95"),
        valid_posts_24h=1000,
        total_communities=200,
        empty_crawls=0,
        avg_latency_seconds=Decimal("1.0"),
    )
    db_session.add(crawl_metric)
    await db_session.commit()
    
    # 执行采集
    metrics = await collect_metrics(db_session, target_date)
    
    # 验证结果
    assert metrics.processing_time_p50 == Decimal("0.00")
    assert metrics.processing_time_p95 == Decimal("0.00")


@pytest.mark.asyncio
async def test_save_metrics_new_record(db_session, tmp_path):
    """测试保存新记录"""
    target_date = date(2025, 10, 21)
    
    metrics = QualityMetrics(
        date=target_date,
        collection_success_rate=Decimal("0.9800"),
        deduplication_rate=Decimal("0.0800"),
        processing_time_p50=Decimal("18.50"),
        processing_time_p95=Decimal("45.20"),
    )
    
    # 保存到临时目录
    output_file = await save_metrics(db_session, metrics, output_dir=tmp_path)
    
    # 验证数据库记录
    result = await db_session.execute(
        select(QualityMetrics).where(QualityMetrics.date == target_date)
    )
    saved_metrics = result.scalar_one()
    
    assert saved_metrics.collection_success_rate == Decimal("0.9800")
    assert saved_metrics.deduplication_rate == Decimal("0.0800")
    
    # 验证文件
    assert output_file.exists()
    with output_file.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["date"] == "2025-10-21"
        assert data["collection_success_rate"] == 0.98


@pytest.mark.asyncio
async def test_save_metrics_update_existing(db_session, tmp_path):
    """测试更新现有记录"""
    target_date = date(2025, 10, 21)
    
    # 先插入一条记录
    existing_metrics = QualityMetrics(
        date=target_date,
        collection_success_rate=Decimal("0.9000"),
        deduplication_rate=Decimal("0.1000"),
        processing_time_p50=Decimal("20.00"),
        processing_time_p95=Decimal("50.00"),
    )
    db_session.add(existing_metrics)
    await db_session.commit()
    
    # 更新记录
    new_metrics = QualityMetrics(
        date=target_date,
        collection_success_rate=Decimal("0.9800"),
        deduplication_rate=Decimal("0.0800"),
        processing_time_p50=Decimal("18.50"),
        processing_time_p95=Decimal("45.20"),
    )
    
    await save_metrics(db_session, new_metrics, output_dir=tmp_path)
    
    # 验证数据库只有一条记录，且已更新
    result = await db_session.execute(
        select(QualityMetrics).where(QualityMetrics.date == target_date)
    )
    all_metrics = result.scalars().all()
    
    assert len(all_metrics) == 1
    assert all_metrics[0].collection_success_rate == Decimal("0.9800")

