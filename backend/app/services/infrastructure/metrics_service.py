"""
Metrics Service

基于 Spec 007 User Story 2 (US2) - Task T024
提供质量指标查询服务，复用 red_line_checker 的 DailyMetrics 数据结构
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from app.services.metrics.daily_metrics import DailyMetrics


def _parse_csv_row(row: dict[str, str]) -> DailyMetrics:
    """解析 CSV 行数据为 DailyMetrics 对象"""
    return DailyMetrics(
        date=date.fromisoformat(row["date"]),
        cache_hit_rate=float(row["cache_hit_rate"]),
        valid_posts_24h=int(row["valid_posts_24h"]),
        total_communities=int(row["total_communities"]),
        duplicate_rate=float(row["duplicate_rate"]),
        precision_at_50=float(row["precision_at_50"]),
        avg_score=float(row["avg_score"]),
    )


def get_daily_metrics(
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    metrics_directory: Path = Path("reports/daily_metrics"),
) -> List[DailyMetrics]:
    """获取指定日期范围内的每日质量指标
    
    从 CSV 文件中读取指标数据（格式：YYYY-MM.csv）
    
    Args:
        start_date: 开始日期（默认为 7 天前）
        end_date: 结束日期（默认为今天）
        metrics_directory: 指标文件目录
    
    Returns:
        List[DailyMetrics]: 按日期升序排列的指标列表
    
    Example:
        >>> metrics = get_daily_metrics(
        ...     start_date=date(2025, 10, 15),
        ...     end_date=date(2025, 10, 21)
        ... )
        >>> len(metrics)
        7
    """
    # 设置默认日期范围（最近 7 天）
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=7)
    
    # 确保目录存在
    if not metrics_directory.exists():
        return []
    
    # 收集需要读取的月份文件
    months_to_read: set[str] = set()
    current = start_date
    while current <= end_date:
        months_to_read.add(f"{current:%Y-%m}")
        # 移动到下个月的第一天
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    
    # 读取所有相关月份的 CSV 文件
    all_metrics: List[DailyMetrics] = []
    for month_str in sorted(months_to_read):
        csv_path = metrics_directory / f"{month_str}.csv"
        if not csv_path.exists():
            continue
        
        try:
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        metric = _parse_csv_row(row)
                        # 只保留在日期范围内的记录
                        if start_date <= metric.date <= end_date:
                            all_metrics.append(metric)
                    except (ValueError, KeyError):
                        # 跳过无效行
                        continue
        except Exception:
            # 跳过无法读取的文件
            continue
    
    # 按日期升序排序
    all_metrics.sort(key=lambda m: m.date)
    return all_metrics


__all__ = ["get_daily_metrics"]

