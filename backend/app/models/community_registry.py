from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Computed, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class CommunityRegistry(TimestampMixin, Base):
    """Canonical community identity registry."""

    __tablename__ = "community_registry"
    __table_args__ = (
        Index("ix_community_registry_key", "community_key"),
        Index("ix_community_registry_enabled", "is_enabled"),
        Index(
            "uq_community_registry_platform_name",
            "platform",
            "community_name",
            unique=True,
        ),
    )

    id: Mapped[int] = int_pk_column()
    platform: Mapped[str] = mapped_column(String(20), default="reddit", nullable=False)
    community_name: Mapped[str] = mapped_column(String(100), nullable=False)
    community_key: Mapped[str] = mapped_column(
        String(100),
        Computed("lower(regexp_replace(community_name, '^r/', ''))", persisted=True),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legacy_pool_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("community_pool.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    source_of_truth: Mapped[str] = mapped_column(
        String(20),
        default="registry",
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


__all__ = ["CommunityRegistry"]
