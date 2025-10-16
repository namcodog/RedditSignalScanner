from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, DateTime, Index, Integer,
                        Numeric, String, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CommunityCache(TimestampMixin, Base):
    """Cache metadata supporting cache-first Reddit fetching."""

    __tablename__ = "community_cache"
    __table_args__ = (
        CheckConstraint(
            "posts_cached >= 0", name="ck_community_cache_posts_cached_non_negative"
        ),
        CheckConstraint("ttl_seconds > 0", name="ck_community_cache_positive_ttl"),
        CheckConstraint(
            "crawl_priority BETWEEN 1 AND 100",
            name="ck_community_cache_priority_range",
        ),
        Index("idx_cache_priority", "crawl_priority"),
        Index("idx_cache_last_crawled", "last_crawled_at"),
        Index("idx_cache_hit_count", "hit_count"),
        Index("idx_cache_quality", "quality_score"),
    )

    community_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    posts_cached: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    quality_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=0.50, nullable=False
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crawl_priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawl_frequency_hours: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 监控与统计字段（T1.2）
    empty_hit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_hit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_hit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_valid_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_tier: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )

    # 水位线字段（用于增量抓取）
    last_seen_post_id: Mapped[str | None] = mapped_column(String(100))
    last_seen_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    total_posts_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dedup_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    def __repr__(self) -> str:
        return f"CommunityCache(community_name={self.community_name!r}, hit_count={self.hit_count})"
