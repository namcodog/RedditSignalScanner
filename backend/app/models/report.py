from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.analysis import Analysis


class Report(TimestampMixin, Base):
    """Pre-rendered HTML report associated with a single analysis."""

    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_generated", "generated_at"),
        Index("idx_reports_template", "template_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk_column()
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    template_version: Mapped[str] = mapped_column(
        String(10), default="1.0", nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="report")

    def __repr__(self) -> str:
        return f"Report(id={self.id!s}, analysis_id={self.analysis_id!s})"
