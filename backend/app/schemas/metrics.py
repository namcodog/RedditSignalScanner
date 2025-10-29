"""
Quality Metrics Schemas

基于 Spec 007 User Story 2 (US2) - Task T023
提供每日质量指标的 Pydantic schema 定义
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DailyMetricsResponse(BaseModel):
    """每日质量指标响应模型

    对应 backend/app/services/metrics/daily_metrics.py 中的 DailyMetrics dataclass

    注意：date 字段使用 str 而非 datetime.date，因为 Pydantic v1 + datetime.date 有 RecursionError bug
    格式：YYYY-MM-DD (ISO 8601)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-10-27",
                "cache_hit_rate": 0.72,
                "valid_posts_24h": 1850,
                "total_communities": 42,
                "duplicate_rate": 0.12,
                "precision_at_50": 0.75,
                "avg_score": 0.58,
            }
        },
    )

    date: str = Field(..., description="指标日期 (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
    cache_hit_rate: float = Field(..., description="缓存命中率 (0.0-1.0)", ge=0.0, le=1.0)
    valid_posts_24h: int = Field(..., description="24小时内有效帖子数", ge=0)
    total_communities: int = Field(..., description="总社区数", ge=0)
    duplicate_rate: float = Field(..., description="重复率 (0.0-1.0)", ge=0.0, le=1.0)
    precision_at_50: float = Field(..., description="Precision@50 指标 (0.0-1.0)", ge=0.0, le=1.0)
    avg_score: float = Field(..., description="平均评分 (0.0-1.0)", ge=0.0, le=1.0)


class DailyMetricsListResponse(BaseModel):
    """每日质量指标列表响应"""
    
    metrics: list[DailyMetricsResponse] = Field(
        default_factory=list,
        description="指标列表",
    )
    total: int = Field(..., description="总记录数", ge=0)


__all__ = ["DailyMetricsResponse", "DailyMetricsListResponse"]
