from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CommunityRuntimeState(TimestampMixin, Base):
    """Runtime-only crawl state keyed by canonical community identity."""

    __tablename__ = "community_runtime_state"
    __table_args__ = (
        CheckConstraint(
            "crawl_status IN ('active','paused','blocked','needs_backfill')",
            name="community_runtime_state_status_valid",
        ),
        CheckConstraint(
            "crawl_priority BETWEEN 1 AND 100",
            name="community_runtime_state_priority_range",
        ),
        Index("ix_community_runtime_state_status", "crawl_status"),
        Index("ix_community_runtime_state_last_crawled", "last_crawled_at"),
    )

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community_registry.id", ondelete="CASCADE"),
        primary_key=True,
    )
    crawl_status: Mapped[str] = mapped_column(String(20), nullable=False)
    crawl_priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    legacy_cache_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sample_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_post_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    backfill_floor: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    runtime_notes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


__all__ = ["CommunityRuntimeState"]
