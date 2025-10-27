"""
Integration tests for metrics API

基于 speckit-006 User Story 1 (US1) - Task T007
"""
from datetime import date, timedelta
from decimal import Decimal

import asyncio
from typing import Iterator

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module", autouse=True)
def _module_event_loop() -> Iterator[None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)
        loop.close()
from httpx import AsyncClient

from app.models.metrics import QualityMetrics


@pytest.mark.asyncio
async def test_get_metrics_default_range(client: AsyncClient, db_session):
    """测试获取默认日期范围的指标（最近 7 天）"""
    # 准备测试数据
    today = date.today()
    for i in range(7):
        metric_date = today - timedelta(days=i)
        metric = QualityMetrics(
            date=metric_date,
            collection_success_rate=Decimal("0.9800"),
            deduplication_rate=Decimal("0.0800"),
            processing_time_p50=Decimal("18.50"),
            processing_time_p95=Decimal("45.20"),
        )
        db_session.add(metric)
    await db_session.commit()

    # 调用 API
    response = await client.get("/api/metrics")

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    assert data[0]["collection_success_rate"] == 0.98
    assert data[0]["deduplication_rate"] == 0.08


@pytest.mark.asyncio
async def test_get_metrics_custom_range(client: AsyncClient, db_session):
    """测试获取自定义日期范围的指标"""
    # 准备测试数据
    start_date = date(2025, 10, 15)
    end_date = date(2025, 10, 21)

    for i in range(7):
        metric_date = start_date + timedelta(days=i)
        metric = QualityMetrics(
            date=metric_date,
            collection_success_rate=Decimal("0.9500"),
            deduplication_rate=Decimal("0.1000"),
            processing_time_p50=Decimal("20.00"),
            processing_time_p95=Decimal("50.00"),
        )
        db_session.add(metric)
    await db_session.commit()

    # 调用 API
    response = await client.get(
        "/api/metrics",
        params={"start_date": "2025-10-15", "end_date": "2025-10-21"},
    )

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    assert data[0]["date"] == "2025-10-15"
    assert data[-1]["date"] == "2025-10-21"


@pytest.mark.asyncio
async def test_get_metrics_empty_result(client: AsyncClient, db_session):
    """测试没有数据时返回空列表"""
    # 不准备任何数据

    # 调用 API
    response = await client.get("/api/metrics")

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_metrics_response_schema(client: AsyncClient, db_session):
    """测试响应 schema 的严格性"""
    # 准备测试数据
    metric = QualityMetrics(
        date=date.today(),
        collection_success_rate=Decimal("0.9800"),
        deduplication_rate=Decimal("0.0800"),
        processing_time_p50=Decimal("18.50"),
        processing_time_p95=Decimal("45.20"),
    )
    db_session.add(metric)
    await db_session.commit()

    # 调用 API
    response = await client.get("/api/metrics")

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    # 验证字段
    item = data[0]
    assert "date" in item
    assert "collection_success_rate" in item
    assert "deduplication_rate" in item
    assert "processing_time_p50" in item
    assert "processing_time_p95" in item

    # 验证数据类型
    assert isinstance(item["date"], str)
    assert isinstance(item["collection_success_rate"], float)
    assert isinstance(item["deduplication_rate"], float)
    assert isinstance(item["processing_time_p50"], float)
    assert isinstance(item["processing_time_p95"], float)

    # 验证数值范围
    assert 0.0 <= item["collection_success_rate"] <= 1.0
    assert 0.0 <= item["deduplication_rate"] <= 1.0
    assert item["processing_time_p50"] >= 0.0
    assert item["processing_time_p95"] >= 0.0
    assert item["processing_time_p95"] >= item["processing_time_p50"]


@pytest.mark.asyncio
async def test_get_metrics_ordered_by_date(client: AsyncClient, db_session):
    """测试结果按日期升序排列"""
    # 准备测试数据（乱序插入）
    dates = [
        date(2025, 10, 21),
        date(2025, 10, 18),
        date(2025, 10, 20),
        date(2025, 10, 19),
    ]

    for metric_date in dates:
        metric = QualityMetrics(
            date=metric_date,
            collection_success_rate=Decimal("0.9800"),
            deduplication_rate=Decimal("0.0800"),
            processing_time_p50=Decimal("18.50"),
            processing_time_p95=Decimal("45.20"),
        )
        db_session.add(metric)
    await db_session.commit()

    # 调用 API
    response = await client.get(
        "/api/metrics",
        params={"start_date": "2025-10-18", "end_date": "2025-10-21"},
    )

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4

    # 验证排序
    assert data[0]["date"] == "2025-10-18"
    assert data[1]["date"] == "2025-10-19"
    assert data[2]["date"] == "2025-10-20"
    assert data[3]["date"] == "2025-10-21"
