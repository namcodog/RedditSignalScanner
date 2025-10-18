from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CrawlMetrics(Base):
    """Hourly/daily crawl metrics for monitoring pipeline health (T1.3).

    Minimal initial fields to support Phase 1 acceptance.
    """

    __tablename__ = "crawl_metrics"
    __table_args__ = (
        Index("idx_metrics_metric_date", "metric_date"),
        Index("idx_metrics_metric_hour", "metric_hour"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


__all__ = ["CrawlMetrics"]
