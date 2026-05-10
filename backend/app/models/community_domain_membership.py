from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class CommunityDomainMembership(TimestampMixin, Base):
    """Bind a canonical community to a business domain."""

    __tablename__ = "community_domain_membership"
    __table_args__ = (
        CheckConstraint(
            "membership_source IN ('seed','manual','reconciled','heuristic','llm')",
            name="membership_source_valid",
        ),
        Index("ix_community_domain_membership_domain", "domain_key"),
        Index(
            "uq_community_domain_membership_community_domain",
            "community_id",
            "domain_key",
            unique=True,
        ),
    )

    id: Mapped[int] = int_pk_column()
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community_registry.id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_key: Mapped[str] = mapped_column(
        ForeignKey("business_categories.key", ondelete="RESTRICT"),
        nullable=False,
    )
    membership_source: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["CommunityDomainMembership"]
