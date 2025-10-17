from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CommunityPool(TimestampMixin, Base):
    __tablename__ = "community_pool"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    categories: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description_keywords: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    daily_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_comment_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(
        Numeric(3, 2), default=0.50, nullable=False
    )
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    user_feedback_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PendingCommunity(Base):
    __tablename__ = "pending_communities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    discovered_from_keywords: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    discovered_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    discovered_from_task_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CommunityImportHistory(Base):
    __tablename__ = "community_import_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by_user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    summary_preview: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
