from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.task import Task


class FactsSnapshot(TimestampMixin, Base):
    """
    facts_v2 的“审计快照”。

    大白话：每跑一次分析，就把“当时用的事实包”和“质量闸门结论”存一份，
    方便后面追查：这份报告到底基于哪些事实、当时有没有缺口/降级。
    """

    __tablename__ = "facts_snapshots"
    __table_args__ = (
        CheckConstraint(
            "schema_version <> ''",
            name="ck_facts_snapshots_schema_version_non_empty",
        ),
        CheckConstraint(
            "tier IN ('A_full','B_trimmed','C_scouting','X_blocked')",
            name="ck_facts_snapshots_valid_tier",
        ),
        CheckConstraint(
            "audit_level IN ('gold','lab','noise')",
            name="ck_facts_snapshots_valid_audit_level",
        ),
        CheckConstraint(
            "status IN ('ok','blocked','failed')",
            name="ck_facts_snapshots_valid_status",
        ),
        CheckConstraint(
            "validator_level IN ('info','warn','error')",
            name="ck_facts_snapshots_valid_validator_level",
        ),
        Index("idx_facts_snapshots_task_id", "task_id"),
        Index("idx_facts_snapshots_created_at", "created_at"),
        Index("idx_facts_snapshots_task_created", "task_id", "created_at"),
        Index("idx_facts_snapshots_tier", "tier"),
        Index("idx_facts_snapshots_passed", "passed"),
        Index("idx_facts_snapshots_audit_level", "audit_level"),
        Index("idx_facts_snapshots_status", "status"),
        Index("idx_facts_snapshots_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的分析任务 ID",
    )
    schema_version: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="2.0",
        server_default="2.0",
        comment="facts_v2 schema version",
    )
    v2_package: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="facts_v2 审计包（v2_package）",
    )
    quality: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="质量闸门结果（passed/tier/flags/metrics + 其它校验信息）",
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否通过质量闸门（tier != X_blocked）",
    )
    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="C_scouting",
        server_default="C_scouting",
        comment="报告等级：A_full/B_trimmed/C_scouting/X_blocked",
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
        comment="审计包状态：ok/blocked/failed",
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
        default=30,
        server_default="30",
        comment="审计包保留天数（90/30/7）",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="审计包过期时间（UTC）",
    )
    blocked_reason: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="被拦截原因（如 quality_gate_blocked）",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="失败/拦截错误码（便于检索）",
    )

    task: Mapped["Task"] = relationship("Task", back_populates="facts_snapshots")


__all__ = ["FactsSnapshot"]
