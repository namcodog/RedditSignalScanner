from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Computed, DateTime, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin, int_pk_column


class CommunityPool(TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "community_pool"
    __table_args__ = (
        Index(
            "idx_community_pool_categories_gin",
            "categories",
            postgresql_using="gin",
        ),
        Index(
            "idx_community_pool_keywords_gin",
            "description_keywords",
            postgresql_using="gin",
        ),
        Index("idx_community_pool_name_key", "name_key"),
        Index("idx_community_pool_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = int_pk_column()
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Canonical key without r/ prefix, lowercased, for consistent joins with comments/subreddit fields.
    name_key: Mapped[str] = mapped_column(
        String(100),
        Computed("lower(regexp_replace(name, '^r/', ''))", persisted=True),
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    categories: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description_keywords: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    daily_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_comment_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(
        "semantic_quality_score",
        Numeric(3, 2),
        default=0.50,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    user_feedback_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blacklist_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    downrank_factor: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # 健康状态评估（基于近期活跃度与质量）
    health_status: Mapped[str] = mapped_column(
        String(20),
        default="unknown",  # healthy | warning | critical | unknown
        nullable=False,
    )

    # 最近一次智能评估时间
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 自动调级开关（仅当开启时才会自动应用高置信度建议）
    auto_tier_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
