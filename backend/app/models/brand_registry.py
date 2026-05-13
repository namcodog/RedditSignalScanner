from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class BrandRegistry(TimestampMixin, Base):
    """Canonical brand pool owned by the main system."""

    __tablename__ = "brand_registry"
    __table_args__ = (
        UniqueConstraint("brand_key", name="uq_brand_registry_brand_key"),
        Index("ix_brand_registry_status", "review_status"),
        Index("ix_brand_registry_active", "is_active"),
    )

    id: Mapped[int] = int_pk_column()
    brand_key: Mapped[str] = mapped_column(String(160), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_lifecycle: Mapped[str] = mapped_column(String(40), nullable=False)
    domains: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False)
    interest_tags: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String(200)), nullable=False)
    risk_flags: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False)
    source_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BrandMention(TimestampMixin, Base):
    """Observed brand evidence from cards, posts, or later product surfaces."""

    __tablename__ = "brand_mentions"
    __table_args__ = (
        UniqueConstraint("mention_key", name="uq_brand_mentions_mention_key"),
        Index("ix_brand_mentions_brand_source", "brand_id", "source"),
        Index("ix_brand_mentions_observed_at", "observed_at"),
    )

    id: Mapped[int] = int_pk_column()
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brand_registry.id", ondelete="CASCADE"),
        nullable=False,
    )
    mention_key: Mapped[str] = mapped_column(String(64), nullable=False)
    brand_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    community: Mapped[str | None] = mapped_column(String(120))
    source_field: Mapped[str | None] = mapped_column(String(40))
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permalink: Mapped[str | None] = mapped_column(Text)
    evidence_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


__all__ = ["BrandMention", "BrandRegistry"]
