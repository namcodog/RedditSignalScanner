from __future__ import annotations

from typing import List, Optional

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SemanticTerm(TimestampMixin, Base):
    """核心语义术语表，存储规范化后的词条及其属性。"""

    __tablename__ = "semantic_terms"
    __table_args__ = (
        Index(
            "ix_semantic_terms_canonical",
            "canonical",
            unique=True,
        ),
        Index("ix_semantic_terms_category_layer", "category", "layer"),
        Index("ix_semantic_terms_lifecycle", "lifecycle"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, nullable=False
    )
    canonical: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    aliases: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(128)), nullable=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    layer: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    precision_tag: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    polarity: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    lifecycle: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="approved",
    )


__all__ = ["SemanticTerm"]

