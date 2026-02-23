from __future__ import annotations

from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, TimestampMixin, int_pk_column


class SemanticCandidate(TimestampMixin, AuditMixin, Base):
    """待审核的语义候选词表。"""

    __tablename__ = "semantic_candidates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_semantic_candidates_status_valid",
        ),
        Index("ix_semantic_candidates_status", "status"),
        Index("ix_semantic_candidates_frequency", "frequency"),
        Index("ix_semantic_candidates_first_seen_at", "first_seen_at"),
    )

    id: Mapped[int] = int_pk_column()
    term: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    approved_layer: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)


__all__ = ["SemanticCandidate"]

