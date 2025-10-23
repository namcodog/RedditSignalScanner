"""
Quality Metrics API Endpoints

基于 speckit-006 User Story 1 (US1) - Task T007
提供质量指标查询接口
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.metrics import QualityMetrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


class QualityMetricsResponse(BaseModel):
    """质量指标响应模型"""

    model_config = ConfigDict(from_attributes=True)

    date: date
    collection_success_rate: float
    deduplication_rate: float
    processing_time_p50: float
    processing_time_p95: float


@router.get("", response_model=List[QualityMetricsResponse])
async def get_quality_metrics(
    start_date: Optional[date] = Query(
        None, description="开始日期（默认为 7 天前）"
    ),
    end_date: Optional[date] = Query(None, description="结束日期（默认为今天）"),
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
        )
        for m in metrics_list
    ]


__all__ = ["router"]

