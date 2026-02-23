from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class TierAuditLog(TimestampMixin, Base):
    """社区 Tier 调整审计日志。

    记录每一次社区 Tier / 优先级 / 激活状态等相关变更，以及
    变更前后的完整快照，用于追踪和回滚。
    """

    __tablename__ = "tier_audit_logs"

    id: Mapped[int] = int_pk_column()

    community_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # 操作类型
    action: Mapped[str] = mapped_column(
        String(50),  # tier_change | priority_change | activate | deactivate | batch_update | rollback
        nullable=False,
        index=True,
    )

    # 变更内容
    field_changed: Mapped[str] = mapped_column(String(50), nullable=False)
    from_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_value: Mapped[str] = mapped_column(String(50), nullable=False)

    # 操作者与原因
    changed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    change_source: Mapped[str] = mapped_column(
        String(20),  # manual | auto | suggestion
        default="manual",
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 快照（支持回滚）
    snapshot_before: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    snapshot_after: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # 关联建议（如果来自自动建议）
    suggestion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 回滚状态
    is_rolled_back: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rolled_back_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


__all__ = ["TierAuditLog"]
