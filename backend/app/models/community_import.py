from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, TimestampMixin, int_pk_column


class CommunityImportHistory(TimestampMixin, AuditMixin, Base):
    """Record of admin Excel imports to support auditing and troubleshooting."""

    __tablename__ = "community_import_history"
    __table_args__ = (
        Index(
            "idx_community_import_history_uploaded_by",
            "uploaded_by_user_id",
        ),
        Index(
            "idx_community_import_history_created_at",
            "created_at",
        ),
    )

    id: Mapped[int] = int_pk_column()
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_details: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    summary_preview: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )


__all__ = ["CommunityImportHistory"]
