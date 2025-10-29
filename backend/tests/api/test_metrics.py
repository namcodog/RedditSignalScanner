"""
Tests for Metrics API Endpoints

基于 Spec 007 User Story 2 (US2) - Task T026
测试每日质量指标 API 端点
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.services.metrics_service import get_daily_metrics


@pytest.fixture
def temp_metrics_dir(tmp_path: Path) -> Path:
    """创建临时指标目录并生成测试数据"""
    metrics_dir = tmp_path / "daily_metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # 生成测试数据：2025-10 月份的 7 天数据
    test_data = [
        {
            "date": "2025-10-15",
            "cache_hit_rate": "0.68",
            "valid_posts_24h": "1850",
            "total_communities": "40",
            "duplicate_rate": "0.12",
            "precision_at_50": "0.72",
            "avg_score": "0.55",
        },
        {
            "date": "2025-10-16",
            "cache_hit_rate": "0.70",
            "valid_posts_24h": "1920",
            "total_communities": "42",
            "duplicate_rate": "0.10",
            "precision_at_50": "0.75",
            "avg_score": "0.58",
        },
        {
            "date": "2025-10-17",
            "cache_hit_rate": "0.65",
            "valid_posts_24h": "1780",
            "total_communities": "38",
            "duplicate_rate": "0.15",
            "precision_at_50": "0.68",
            "avg_score": "0.52",
        },
        {
            "date": "2025-10-18",
            "cache_hit_rate": "0.72",
            "valid_posts_24h": "2000",
            "total_communities": "45",
            "duplicate_rate": "0.08",
            "precision_at_50": "0.78",
            "avg_score": "0.60",
        },
        {
            "date": "2025-10-19",
            "cache_hit_rate": "0.69",
            "valid_posts_24h": "1900",
            "total_communities": "41",
            "duplicate_rate": "0.11",
            "precision_at_50": "0.73",
            "avg_score": "0.56",
        },
        {
            "date": "2025-10-20",
            "cache_hit_rate": "0.71",
            "valid_posts_24h": "1950",
            "total_communities": "43",
            "duplicate_rate": "0.09",
            "precision_at_50": "0.76",
            "avg_score": "0.59",
        },
        {
            "date": "2025-10-21",
            "cache_hit_rate": "0.67",
            "valid_posts_24h": "1820",
            "total_communities": "39",
            "duplicate_rate": "0.13",
            "precision_at_50": "0.70",
            "avg_score": "0.54",
        },
    ]

    # 写入 CSV 文件
    csv_path = metrics_dir / "2025-10.csv"
    fieldnames = [
        "date",
        "cache_hit_rate",
        "valid_posts_24h",
        "total_communities",
        "duplicate_rate",
        "precision_at_50",
        "avg_score",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_data)

    return metrics_dir


def test_get_daily_metrics_service_custom_range(temp_metrics_dir: Path) -> None:
    """测试 service 层：自定义日期范围"""
    # Act
    metrics = get_daily_metrics(
        start_date=date(2025, 10, 15),
        end_date=date(2025, 10, 18),
        metrics_directory=temp_metrics_dir,
    )

    # Assert
    assert len(metrics) == 4

    # 验证数据按日期升序排列
    dates = [m.date for m in metrics]
    assert dates == [
        date(2025, 10, 15),
        date(2025, 10, 16),
        date(2025, 10, 17),
        date(2025, 10, 18),
    ]

    # 验证第一条数据的字段
    first_metric = metrics[0]
    assert first_metric.date == date(2025, 10, 15)
    assert first_metric.cache_hit_rate == 0.68
    assert first_metric.valid_posts_24h == 1850
    assert first_metric.total_communities == 40
    assert first_metric.duplicate_rate == 0.12
    assert first_metric.precision_at_50 == 0.72
    assert first_metric.avg_score == 0.55


def test_get_daily_metrics_service_empty_directory(tmp_path: Path) -> None:
    """测试 service 层：空目录（无数据）"""
    empty_dir = tmp_path / "empty_metrics"
    empty_dir.mkdir(parents=True, exist_ok=True)

    # Act
    metrics = get_daily_metrics(
        start_date=date(2025, 10, 15),
        end_date=date(2025, 10, 21),
        metrics_directory=empty_dir,
    )

    # Assert
    assert len(metrics) == 0


def test_get_daily_metrics_service_data_validation(temp_metrics_dir: Path) -> None:
    """测试 service 层：数据字段验证"""
    # Act
    metrics = get_daily_metrics(
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 20),
        metrics_directory=temp_metrics_dir,
    )

    # Assert
    assert len(metrics) == 1

    metric = metrics[0]
    # 验证数值范围
    assert 0.0 <= metric.cache_hit_rate <= 1.0
    assert 0.0 <= metric.duplicate_rate <= 1.0
    assert 0.0 <= metric.precision_at_50 <= 1.0
    assert 0.0 <= metric.avg_score <= 1.0
    assert metric.valid_posts_24h >= 0
    assert metric.total_communities >= 0

