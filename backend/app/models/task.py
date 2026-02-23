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
    from app.models.facts_snapshot import FactsSnapshot
    from app.models.facts_run_log import FactsRunLog
    from app.models.insight import InsightCard
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
            "'network_error', 'processing_error', 'data_validation_error', 'system_error', "
            "'insufficient_data', 'worker_stalled', 'system_dependency_down'"
            ")"
            ")",
            name="ck_tasks_failure_category_whitelist",
        ),
        CheckConstraint(
            "mode IN ('market_insight', 'operations')",
            name="ck_tasks_valid_mode",
        ),
        CheckConstraint(
            "audit_level IN ('gold', 'lab', 'noise')",
            name="ck_tasks_valid_audit_level",
        ),
        CheckConstraint(
            "(topic_profile_id IS NULL) OR (topic_profile_id <> '')",
            name="ck_tasks_valid_topic_profile_id",
        ),
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_user_created", "user_id", "created_at"),
        Index("ix_tasks_status_created", "status", "created_at"),
        Index("ix_tasks_topic_profile_id", "topic_profile_id"),
        Index("ix_tasks_audit_level", "audit_level"),
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
    mode: Mapped[str] = mapped_column(
        String(50),
        default="market_insight",
        nullable=False,
    )
    audit_level: Mapped[str] = mapped_column(
        String(20),
        default="lab",
        nullable=False,
    )
    topic_profile_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
    insight_cards: Mapped[list["InsightCard"]] = relationship(
        "InsightCard", back_populates="task", cascade="all, delete-orphan"
    )
    facts_snapshots: Mapped[list["FactsSnapshot"]] = relationship(
        "FactsSnapshot",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="FactsSnapshot.created_at.desc()",
    )
    facts_run_logs: Mapped[list["FactsRunLog"]] = relationship(
        "FactsRunLog",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="FactsRunLog.created_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"Task(id={self.id!s}, user_id={self.user_id!s}, mode={self.mode!r}, audit_level={self.audit_level!r}, topic_profile_id={self.topic_profile_id!r}, status={self.status.value!r})"
        )
