from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CrawlerRun(Base):
    __tablename__ = "crawler_runs"
    __table_args__ = (
        Index("idx_crawler_runs_status", "status"),
        Index("idx_crawler_runs_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
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


__all__ = ["CrawlerRun"]
