from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin, int_pk_column


class DiscoveredCommunity(TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    """
    Discovered communities waiting for evaluation.
    
    Lifecycle:
    1. pending -> Community discovered, awaiting evaluation
    2. approved -> Passed evaluation, promoted to CommunityPool
    3. rejected -> Failed evaluation, subject to cooldown
    4. blacklisted -> Failed 3+ times, permanently excluded
    """
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

    # ========== Phase 6 Evaluation Fields ==========
    # Stores evaluation metrics like value_density, subscribers, active_count
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Category tags (e.g., ["Ecommerce_Business", "Tools_EDC"])
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    
    # Cooldown period end time (rejected communities skip re-evaluation until this time)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Consecutive rejection count (>= 3 -> blacklisted)
    rejection_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# NOTE: The auto-promotion trigger (_ensure_pool_row_before_discovered) has been REMOVED.
# Reason: Phase 6 requires "evaluate first, promote later" workflow.
# New communities are now inserted as status='pending' and only promoted to
# CommunityPool after passing the CommunityEvaluator assessment.


__all__ = ["DiscoveredCommunity"]
