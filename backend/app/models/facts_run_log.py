from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.task import Task


class FactsRunLog(TimestampMixin, Base):
    """facts_v2 最小运行日志（主要给 noise/lab 任务留痕）。"""

    __tablename__ = "facts_run_logs"
    __table_args__ = (
        CheckConstraint(
            "audit_level IN ('gold','lab','noise')",
            name="ck_facts_run_logs_valid_audit_level",
        ),
        CheckConstraint(
            "status IN ('ok','blocked','failed','skipped')",
            name="ck_facts_run_logs_valid_status",
        ),
        CheckConstraint(
            "validator_level IN ('info','warn','error')",
            name="ck_facts_run_logs_valid_validator_level",
        ),
        Index("idx_facts_run_logs_task_id", "task_id"),
        Index("idx_facts_run_logs_created_at", "created_at"),
        Index("idx_facts_run_logs_expires_at", "expires_at"),
        Index("idx_facts_run_logs_audit_level", "audit_level"),
        Index("idx_facts_run_logs_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的分析任务 ID",
    )
    audit_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="lab",
        server_default="lab",
        comment="审计档位：gold/lab/noise",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ok",
        server_default="ok",
        comment="运行状态：ok/blocked/failed/skipped",
    )
    validator_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="info",
        server_default="info",
        comment="validator 级别：info/warn/error",
    )
    retention_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=7,
        server_default="7",
        comment="日志保留天数（默认 7 天）",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="日志过期时间（UTC）",
    )
    summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="最小运行摘要（计数/配置/范围等）",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="失败/拦截错误码（便于检索）",
    )
    error_message_short: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="一行错误摘要",
    )

    task: Mapped["Task"] = relationship("Task", back_populates="facts_run_logs")


__all__ = ["FactsRunLog"]
