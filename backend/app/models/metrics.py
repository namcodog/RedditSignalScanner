"""
Quality Metrics Model

基于 speckit-006 User Story 1 (US1)
用于存储每日质量指标数据
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class QualityMetrics(TimestampMixin, Base):
    """每日质量指标模型
    
    用于存储系统运行的核心质量指标：
    - 采集成功率: 从 Reddit API 成功抓取数据的比例
    - 重复率: 去重后被过滤掉的帖子比例
    - 处理耗时: 分析任务的 P50 和 P95 耗时
    
    数据来源:
    - CrawlMetrics 表（爬虫指标）
    - Task 表（任务耗时）
    """

    __tablename__ = "quality_metrics"
    __table_args__ = (
        CheckConstraint(
            "collection_success_rate BETWEEN 0.00 AND 1.00",
            name="ck_quality_metrics_collection_success_rate_range",
        ),
        CheckConstraint(
            "deduplication_rate BETWEEN 0.00 AND 1.00",
            name="ck_quality_metrics_deduplication_rate_range",
        ),
        CheckConstraint(
            "processing_time_p50 >= 0",
            name="ck_quality_metrics_processing_time_p50_non_negative",
        ),
        CheckConstraint(
            "processing_time_p95 >= 0",
            name="ck_quality_metrics_processing_time_p95_non_negative",
        ),
        CheckConstraint(
            "processing_time_p95 >= processing_time_p50",
            name="ck_quality_metrics_p95_gte_p50",
        ),
        Index("idx_quality_metrics_date", "date", unique=True),
    )

    id: Mapped[int] = int_pk_column()
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)

    # 采集成功率 (0.0 - 1.0)
    # 计算公式: successful_crawls / (successful_crawls + failed_crawls)
    collection_success_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False
    )

    # 重复率 (0.0 - 1.0)
    # 计算公式: total_duplicates / (total_new_posts + total_duplicates)
    deduplication_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    # 处理耗时 P50（中位数，单位：秒）
    processing_time_p50: Mapped[Decimal] = mapped_column(
        Numeric(7, 2), nullable=False
    )

    # 处理耗时 P95（95分位数，单位：秒）
    processing_time_p95: Mapped[Decimal] = mapped_column(
        Numeric(7, 2), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"QualityMetrics(date={self.date!s}, "
            f"collection_success_rate={self.collection_success_rate}, "
            f"deduplication_rate={self.deduplication_rate})"
        )


__all__ = ["QualityMetrics"]
