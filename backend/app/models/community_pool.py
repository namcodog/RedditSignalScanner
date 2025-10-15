from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

from app.db.session import engine  # ensure metadata binds when needed

Base = declarative_base()


class CommunityPool(Base):
    __tablename__ = "community_pool"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    tier = Column(String(20), nullable=False)
    categories = Column(JSON, nullable=False)
    description_keywords = Column(JSON, nullable=False)
    daily_posts = Column(Integer, default=0, nullable=False)
    avg_comment_length = Column(Integer, default=0, nullable=False)
    quality_score = Column(Numeric(3, 2), default=0.50, nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    user_feedback_count = Column(Integer, default=0, nullable=False)
    discovered_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PendingCommunity(Base):
    __tablename__ = "pending_communities"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    discovered_from_keywords = Column(JSON, nullable=True)
    discovered_count = Column(Integer, default=1, nullable=False)
    first_discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    admin_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    admin_notes = Column(String, nullable=True)


class CommunityImportHistory(Base):
    __tablename__ = "community_import_history"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    uploaded_by = Column(String(255), nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    dry_run = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False)
    total_rows = Column(Integer, nullable=False, default=0)
    valid_rows = Column(Integer, nullable=False, default=0)
    invalid_rows = Column(Integer, nullable=False, default=0)
    duplicate_rows = Column(Integer, nullable=False, default=0)
    imported_rows = Column(Integer, nullable=False, default=0)
    error_details = Column(JSONB, nullable=True)
    summary_preview = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
