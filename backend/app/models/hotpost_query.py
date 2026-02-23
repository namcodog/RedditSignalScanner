from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Index, Text, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk_column


class HotpostQuery(Base):
    __tablename__ = "hotpost_queries"
    __table_args__ = (
        Index("idx_hotpost_query_created", "created_at"),
        Index("idx_hotpost_query_mode", "mode"),
        Index("idx_hotpost_query_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()

    query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    time_filter: Mapped[str] = mapped_column(String(10), nullable=False)
    subreddits: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    community_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)

    from_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = ["HotpostQuery"]
