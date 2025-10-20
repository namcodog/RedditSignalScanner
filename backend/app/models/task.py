from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.analysis import Analysis
    from app.models.user import User


class TaskStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(TimestampMixin, Base):
    """Represents a single analysis request scoped to a user."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "char_length(product_description) BETWEEN 10 AND 2000",
            name="ck_tasks_valid_description_length",
        ),
        CheckConstraint(
            "(completed_at IS NULL) OR (completed_at >= created_at)",
            name="ck_tasks_valid_completion_time",
        ),
        CheckConstraint(
            "((status::text = 'failed') AND error_message IS NOT NULL) OR "
            "((status::text <> 'failed') AND (error_message IS NULL OR error_message = ''))",
            name="ck_tasks_error_message_when_failed",
        ),
        CheckConstraint(
            "((status::text = 'completed') AND completed_at IS NOT NULL) OR "
            "((status::text <> 'completed') AND completed_at IS NULL)",
            name="ck_tasks_completed_status_alignment",
        ),
        CheckConstraint("retry_count >= 0", name="ck_tasks_retry_count_non_negative"),
        CheckConstraint(
            "("
            "failure_category IS NULL OR "
            "failure_category IN ("
            "'network_error', 'processing_error', 'data_validation_error', 'system_error'"
            ")"
            ")",
            name="ck_tasks_failure_category_whitelist",
        ),
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_user_created", "user_id", "created_at"),
        Index("ix_tasks_status_created", "status", "created_at"),
        Index(
            "ix_tasks_processing",
            "status",
            "created_at",
            postgresql_where=text("status::text = 'processing'"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            name="task_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=TaskStatus.PENDING.value,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_category: Mapped[str | None] = mapped_column(String(50))
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dead_letter_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", backref="tasks", lazy="joined")
    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Task(id={self.id!s}, user_id={self.user_id!s}, status={self.status.value!r})"
