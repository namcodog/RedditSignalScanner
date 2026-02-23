from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class TierSuggestion(TimestampMixin, Base):
    """Tier 调级建议记录表。

    存储针对单个社区的推荐 tier 及其置信度、理由和指标快照，
    供管理员在后台审核和应用。
    """

    __tablename__ = "tier_suggestions"

    id: Mapped[int] = int_pk_column()

    community_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    current_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    suggested_tier: Mapped[str] = mapped_column(String(20), nullable=False)

    # 决策依据
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # 状态管理
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",  # pending | accepted | rejected | applied | auto_applied
        nullable=False,
        index=True,
    )

    # 审核信息
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 附加信息
    priority_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


__all__ = ["TierSuggestion"]

