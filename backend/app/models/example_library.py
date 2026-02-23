from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, List

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, TimestampMixin, uuid_pk_column


class ExampleLibrary(TimestampMixin, AuditMixin, Base):
    """Public example library used to seed reliable demo reports."""

    __tablename__ = "example_library"

    id: Mapped[uuid.UUID] = uuid_pk_column()
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)

    analysis_insights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    analysis_sources: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    analysis_action_items: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )
    analysis_confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    analysis_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    report_html: Mapped[str] = mapped_column(Text, nullable=False)
    report_template_version: Mapped[str] = mapped_column(
        String(10), default="1.0", nullable=False
    )

    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"ExampleLibrary(id={self.id!s}, title={self.title!r}, active={self.is_active})"
