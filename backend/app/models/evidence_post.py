from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, int_pk_column


class EvidencePost(TimestampMixin, Base):
    """
    探针证据帖（可审计资产）。

    口径：
    - 探针只负责“产证据 + 产候选社区”，不碰水位线。
    - evidence_posts 用稳定唯一键去重：同一 source/query 下同一 post 只记录一次。
    """

    __tablename__ = "evidence_posts"
    __table_args__ = (
        UniqueConstraint(
            "probe_source",
            "source_query_hash",
            "source_post_id",
            name="uq_evidence_posts_probe_query_post",
        ),
        Index("idx_evidence_posts_probe_query", "probe_source", "source_query_hash"),
        Index("idx_evidence_posts_subreddit_created", "subreddit", "created_at"),
        Index("idx_evidence_posts_target_id", "target_id"),
        Index("idx_evidence_posts_crawl_run_id", "crawl_run_id"),
    )

    id: Mapped[int] = int_pk_column()

    crawl_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawler_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawler_run_targets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # search / hot
    probe_source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_query_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Reddit post id (t3_xxx stripped to xxx in our client) / or any other source id
    source_post_id: Mapped[str] = mapped_column(String(100), nullable=False)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    post_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    evidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


__all__ = ["EvidencePost"]
