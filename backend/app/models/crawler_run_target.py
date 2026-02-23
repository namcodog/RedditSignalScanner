from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CrawlerRunTarget(Base):
    __tablename__ = "crawler_run_targets"
    __table_args__ = (
        Index("idx_crawler_run_targets_crawl_run_id", "crawl_run_id"),
        Index("idx_crawler_run_targets_subreddit", "subreddit"),
        Index("idx_crawler_run_targets_status", "status"),
        Index("idx_crawler_run_targets_started_at", "started_at"),
        Index(
            "uq_crawler_run_targets_run_idempotency_key",
            "crawl_run_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index(
            "idx_crawler_run_targets_plan_kind",
            "plan_kind",
            postgresql_where=text("plan_kind IS NOT NULL"),
        ),
        Index(
            "uq_crawler_run_targets_dedupe_key_active",
            "dedupe_key",
            unique=True,
            postgresql_where=text(
                "dedupe_key IS NOT NULL AND status IN ('queued','running')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    crawl_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawler_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    subreddit: Mapped[str] = mapped_column(Text(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default=text("'running'"), nullable=False
    )
    config: Mapped[dict] = mapped_column(
        JSONB(astext_type=Text()),
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    metrics: Mapped[dict] = mapped_column(
        JSONB(astext_type=Text()),
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message_short: Mapped[str | None] = mapped_column(Text(), nullable=True)
    plan_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(Text(), nullable=True)
    idempotency_key_human: Mapped[str | None] = mapped_column(Text(), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(Text(), nullable=True)
    enqueued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


__all__ = ["CrawlerRunTarget"]
