from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin, int_pk_column


class DiscoveredCommunity(TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "discovered_communities"
    __table_args__ = (
        Index("idx_discovered_communities_task_id", "discovered_from_task_id"),
        Index("idx_discovered_communities_reviewed_by", "reviewed_by"),
        Index("idx_discovered_communities_status", "status"),
        Index("idx_discovered_communities_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = int_pk_column()
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    discovered_from_keywords: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    discovered_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    discovered_from_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


__all__ = ["DiscoveredCommunity"]
