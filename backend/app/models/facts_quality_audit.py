"""ORM model for facts_quality_audit table."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FactsQualityAudit(Base):
    """Quality audit records for facts_v2 generation runs."""

    __tablename__ = "facts_quality_audit"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str | None] = mapped_column(String(512), nullable=True)
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trend_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trend_degraded: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_window_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posts_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solutions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    community_coverage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    degraded: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data_fallback: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    posts_fallback: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    solutions_fallback: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dynamic_whitelist: Mapped[str | None] = mapped_column(Text, nullable=True)
    dynamic_blacklist: Mapped[str | None] = mapped_column(Text, nullable=True)
    insufficient_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True)


__all__ = ["FactsQualityAudit"]
