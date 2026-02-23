from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SemanticConcept(TimestampMixin, Base):
    """Semantic concept SSOT (used for concept_id linkages)."""

    __tablename__ = "semantic_concepts"
    __table_args__ = (
        Index("uq_semantic_concepts_code", "code", unique=True),
        Index("ix_semantic_concepts_domain", "domain"),
        Index("ix_semantic_concepts_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        server_default="general",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )


__all__ = ["SemanticConcept"]

