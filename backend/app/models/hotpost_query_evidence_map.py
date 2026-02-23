from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, UniqueConstraint, String, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk_column


class HotpostQueryEvidenceMap(Base):
    __tablename__ = "hotpost_query_evidence_map"
    __table_args__ = (
        Index("idx_map_query", "query_id"),
        Index("idx_map_evidence", "evidence_id"),
        UniqueConstraint("query_id", "evidence_id", name="uq_hotpost_query_evidence"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()

    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotpost_queries.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_posts.id", ondelete="CASCADE"),
        nullable=False,
    )

    rank: Mapped[int | None] = mapped_column(nullable=True)
    signal_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    signals: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    top_comment_refs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = ["HotpostQueryEvidenceMap"]
