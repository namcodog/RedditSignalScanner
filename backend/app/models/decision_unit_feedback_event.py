from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk_column


class DecisionUnitFeedbackEvent(TimestampMixin, Base):
    """Append-only feedback events for DecisionUnits (Phase107#5)."""

    __tablename__ = "decision_unit_feedback_events"
    __table_args__ = (
        CheckConstraint(
            "label IN ('correct','incorrect','mismatch','valuable','worthless')",
            name="ck_decision_unit_feedback_events_label_valid",
        ),
        Index("idx_du_feedback_decision_unit_id", "decision_unit_id"),
        Index("idx_du_feedback_task_id", "task_id"),
        Index("idx_du_feedback_user_id", "user_id"),
        Index("idx_du_feedback_created_at", "created_at"),
        Index("idx_du_feedback_du_created", "decision_unit_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()

    decision_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("insight_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_profile_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidences.id", ondelete="SET NULL"),
        nullable=True,
    )

    label: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )


__all__ = ["DecisionUnitFeedbackEvent"]

