from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class CommunityGovernanceDecision(TimestampMixin, Base):
    """Governance history for whether a membership is allowed to participate."""

    __tablename__ = "community_governance_decision"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved','review','blocked','archived')",
            name="community_governance_decision_valid",
        ),
        Index(
            "ix_community_governance_decision_membership_current",
            "membership_id",
            "is_current",
        ),
    )

    id: Mapped[int] = int_pk_column()
    membership_id: Mapped[int] = mapped_column(
        ForeignKey("community_domain_membership.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


__all__ = ["CommunityGovernanceDecision"]
