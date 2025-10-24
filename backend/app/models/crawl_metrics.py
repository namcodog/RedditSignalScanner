from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Date, Index, Integer, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class CrawlMetrics(TimestampMixin, Base):
    """Hourly/daily crawl metrics for monitoring pipeline health (T1.3).

    Minimal initial fields to support Phase 1 acceptance.
    """

    __tablename__ = "crawl_metrics"
    __table_args__ = (
        Index("idx_metrics_metric_date", "metric_date"),
        Index("idx_metrics_metric_hour", "metric_hour"),
    )

    id: Mapped[int] = int_pk_column()
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-23

    cache_hit_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), default=0.00, nullable=False
    )
    valid_posts_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_communities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_crawls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    empty_crawls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_crawls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_latency_seconds: Mapped[float] = mapped_column(
        Numeric(7, 2), default=0.00, nullable=False
    )

    # Phase 3 新增字段：详细统计
    total_new_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_updated_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier_assignments: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )

__all__ = ["CrawlMetrics"]
