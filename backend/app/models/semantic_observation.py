from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SemanticObservation(Base):
    """Unified semantic observation ledger for posts/comments."""

    __tablename__ = "semantic_observation"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('post','comment')",
            name="semantic_observation_content_type_valid",
        ),
        CheckConstraint(
            "provenance IN ('rule','llm','import','reconciled')",
            name="semantic_observation_provenance_valid",
        ),
        Index(
            "ix_semantic_observation_content",
            "content_type",
            "content_id",
        ),
        Index("ix_semantic_observation_observation_type", "observation_type"),
        Index("ix_semantic_observation_term_id", "term_id"),
        Index("ix_semantic_observation_concept_id", "concept_id"),
        Index("ix_semantic_observation_run_key", "run_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    observation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    term_id: Mapped[int | None] = mapped_column(
        ForeignKey("semantic_terms.id", ondelete="SET NULL"),
        nullable=True,
    )
    concept_id: Mapped[int | None] = mapped_column(
        ForeignKey("semantic_concepts.id", ondelete="SET NULL"),
        nullable=True,
    )
    label_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    provenance: Mapped[str] = mapped_column(String(20), nullable=False)
    run_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


__all__ = ["SemanticObservation"]
