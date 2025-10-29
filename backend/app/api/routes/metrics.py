"""
Quality Metrics API Endpoints

基于 speckit-006 User Story 1 (US1) - Task T007
提供质量指标查询接口

基于 Spec 007 User Story 2 (US2) - Task T025
新增每日质量指标查询接口 GET /api/metrics/daily
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.metrics import QualityMetrics
from app.schemas.metrics import DailyMetricsResponse, DailyMetricsListResponse
from app.services.metrics_service import get_daily_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])

ALLOWED_METRICS: dict[str, str] = {
    "collection_success_rate": "collection_success_rate",
    "deduplication_rate": "deduplication_rate",
    "processing_time_p50": "processing_time_p50",
    "processing_time_p95": "processing_time_p95",
}


class QualityMetricsResponse(BaseModel):
    """质量指标响应模型"""

    model_config = ConfigDict(from_attributes=True)

    date: date
    collection_success_rate: float
    deduplication_rate: float
    processing_time_p50: float
    processing_time_p95: float
    metrics: dict[str, float] = Field(default_factory=dict, description="按照查询参数过滤后的指标映射")


@router.get("", response_model=List[QualityMetricsResponse])
async def get_quality_metrics(
    start_date: Optional[date] = Query(
        None, description="开始日期（默认为 7 天前）"
    ),
    end_date: Optional[date] = Query(None, description="结束日期（默认为今天）"),
    metrics: Optional[List[str]] = Query(
        None, description="按名称过滤返回的指标，支持重复指定"
    ),
    db: AsyncSession = Depends(get_session),
) -> List[QualityMetricsResponse]:
    """获取质量指标
    
    Args:
        start_date: 开始日期（默认为 7 天前）
        end_date: 结束日期（默认为今天）
        db: 数据库会话
    
    Returns:
        List[QualityMetricsResponse]: 质量指标列表
    
    Example:
        GET /api/metrics
        GET /api/metrics?start_date=2025-10-15&end_date=2025-10-21
    """
    # 设置默认日期范围（最近 7 天）
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    # 校验 metrics 参数
    if metrics is None:
        selected_metrics = list(ALLOWED_METRICS.keys())
    else:
        normalised = [item.strip() for item in metrics if item and item.strip()]
        normalised = list(dict.fromkeys(normalised))
        unknown = [item for item in normalised if item not in ALLOWED_METRICS]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown metrics requested: {', '.join(unknown)}",
            )
        selected_metrics = normalised or list(ALLOWED_METRICS.keys())

    # 查询数据库
    query = (
        select(QualityMetrics)
        .where(
            QualityMetrics.date >= start_date,
            QualityMetrics.date <= end_date,
        )
        .order_by(QualityMetrics.date.asc())
    )

    result = await db.execute(query)
    metrics_list = result.scalars().all()

    # 转换为响应模型
    return [
        QualityMetricsResponse(
            date=m.date,
            collection_success_rate=float(m.collection_success_rate),
            deduplication_rate=float(m.deduplication_rate),
            processing_time_p50=float(m.processing_time_p50),
            processing_time_p95=float(m.processing_time_p95),
            metrics={
                metric_name: float(getattr(m, ALLOWED_METRICS[metric_name]))
                for metric_name in selected_metrics
            },
        )
        for m in metrics_list
    ]


@router.get("/daily", response_model=DailyMetricsListResponse)
async def get_daily_quality_metrics(
    start_date: Optional[date] = Query(
        None, description="开始日期（默认为 7 天前）"
    ),
    end_date: Optional[date] = Query(None, description="结束日期（默认为今天）"),
) -> DailyMetricsListResponse:
    """获取每日质量指标

    基于 Spec 007 User Story 2 (US2) - Task T025
    从 CSV 文件读取每日指标数据，用于质量看板展示

    Args:
        start_date: 开始日期（默认为 7 天前）
        end_date: 结束日期（默认为今天）

    Returns:
        DailyMetricsListResponse: 每日指标列表

    Example:
        GET /api/metrics/daily
        GET /api/metrics/daily?start_date=2025-10-15&end_date=2025-10-21
    """
    # 设置默认日期范围（最近 7 天）
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    # 从 CSV 文件读取指标
    metrics_list = get_daily_metrics(
        start_date=start_date,
        end_date=end_date,
        metrics_directory=Path("reports/daily_metrics"),
    )

    # 转换为响应模型
    return DailyMetricsListResponse(
        metrics=[
            DailyMetricsResponse(
                date=m.date.isoformat(),  # 转换 date 对象为 ISO 8601 字符串 (YYYY-MM-DD)
                cache_hit_rate=m.cache_hit_rate,
                valid_posts_24h=m.valid_posts_24h,
                total_communities=m.total_communities,
                duplicate_rate=m.duplicate_rate,
                precision_at_50=m.precision_at_50,
                avg_score=m.avg_score,
            )
            for m in metrics_list
        ],
        total=len(metrics_list),
    )


__all__ = ["router"]
