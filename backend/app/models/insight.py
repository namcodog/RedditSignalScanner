from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.task import Task


class InsightCard(TimestampMixin, Base):
    """
    洞察卡片模型：存储分析生成的洞察卡片。
    
    每个洞察卡片包含：
    - 标题和摘要
    - 置信度分数
    - 时间窗口（数据来源的时间范围）
    - 相关子版块列表
    - 关联的证据列表
    """

    __tablename__ = "insight_cards"
    __table_args__ = (
        UniqueConstraint("task_id", "title", name="uq_insight_cards_task_title"),
        CheckConstraint(
            "(confidence >= 0.0) AND (confidence <= 1.0)",
            name="ck_insight_cards_confidence_range",
        ),
        CheckConstraint(
            "time_window_days > 0",
            name="ck_insight_cards_time_window_positive",
        ),
        Index("idx_insight_cards_task_id", "task_id"),
        Index("idx_insight_cards_confidence", "confidence"),
        Index("idx_insight_cards_created_at", "created_at"),
        Index("idx_insight_cards_subreddits_gin", "subreddits", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的分析任务 ID",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="洞察卡片标题",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="洞察摘要",
    )
    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        comment="置信度分数 (0.0-1.0)",
    )
    time_window_days: Mapped[int] = mapped_column(
        nullable=False,
        default=30,
        comment="时间窗口（天数）",
    )
    subreddits: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
        comment="相关子版块列表",
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="insight_cards")
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="insight_card",
        cascade="all, delete-orphan",
        order_by="Evidence.score.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"InsightCard("
            f"id={self.id!s}, "
            f"task_id={self.task_id!s}, "
            f"title={self.title!r}, "
            f"confidence={self.confidence}, "
            f"evidences_count={len(self.evidences) if self.evidences else 0}"
            f")"
        )


class Evidence(TimestampMixin, Base):
    """
    证据模型：存储洞察卡片的证据段落。
    
    每条证据包含：
    - 原帖 URL
    - 摘录内容
    - 时间戳
    - 子版块
    - 分数（用于排序）
    """

    __tablename__ = "evidences"
    __table_args__ = (
        CheckConstraint(
            "(score >= 0.0) AND (score <= 1.0)",
            name="ck_evidences_score_range",
        ),
        Index("idx_evidences_insight_card_id", "insight_card_id"),
        Index("idx_evidences_score", "score"),
        Index("idx_evidences_timestamp", "timestamp"),
        Index("idx_evidences_subreddit", "subreddit"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    insight_card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insight_cards.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的洞察卡片 ID",
    )
    post_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="原帖 URL",
    )
    excerpt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="摘录内容",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="帖子时间戳",
    )
    subreddit: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="子版块名称",
    )
    score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.0,
        comment="证据分数 (0.0-1.0)",
    )

    # Relationships
    insight_card: Mapped["InsightCard"] = relationship(
        "InsightCard",
        back_populates="evidences",
    )

    def __repr__(self) -> str:
        return (
            f"Evidence("
            f"id={self.id!s}, "
            f"insight_card_id={self.insight_card_id!s}, "
            f"subreddit={self.subreddit!r}, "
            f"score={self.score}, "
            f"timestamp={self.timestamp}"
            f")"
        )


__all__ = ["InsightCard", "Evidence"]

