from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk_column


class BetaFeedback(TimestampMixin, Base):  # type: ignore[misc]
    """Beta tester feedback for warmup period (PRD-09 Day 17-18)."""

    __tablename__ = "beta_feedback"
    __table_args__ = (
        CheckConstraint(
            "satisfaction >= 1 AND satisfaction <= 5",
            name="ck_beta_feedback_satisfaction_range",
        ),
        Index("idx_beta_feedback_task_id", "task_id"),
        Index("idx_beta_feedback_user_id", "user_id"),
        Index("idx_beta_feedback_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    satisfaction: Mapped[int] = mapped_column(nullable=False)  # 1-5 scale
    missing_communities: Mapped[List[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"BetaFeedback(id={self.id!s}, task_id={self.task_id!s}, satisfaction={self.satisfaction})"
