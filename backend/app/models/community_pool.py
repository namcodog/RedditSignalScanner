from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Index, Integer, Numeric, String
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
        Index("idx_community_pool_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = int_pk_column()
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    categories: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description_keywords: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    daily_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_comment_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(
        Numeric(3, 2), default=0.50, nullable=False
    )
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    user_feedback_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blacklist_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    downrank_factor: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

