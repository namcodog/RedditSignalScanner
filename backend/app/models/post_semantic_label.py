from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.db.base import Base


class PostSemanticLabel(Base):
    __tablename__ = "post_semantic_labels"

    id = Column(BigInteger, primary_key=True)
    post_id = Column(
        BigInteger,
        ForeignKey("posts_raw.id", name="fk_post_semantic_labels_post", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    l1_category = Column(String(50))
    l2_business = Column(String(50))
    l3_scene = Column(String(100))
    matched_rule_ids = Column(ARRAY(Integer))
    top_terms = Column(ARRAY(Text))
    raw_scores = Column(JSONB)
    rule_version = Column(String(50), nullable=False, server_default="unknown")
    llm_version = Column(String(50), nullable=False, server_default="unknown")
    sentiment_score = Column(Float)
    confidence = Column(Float)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("post_id", name="uq_post_semantic_labels_post"),
        Index("idx_psl_l1", "l1_category"),
        Index("idx_psl_l2", "l2_business"),
        Index("idx_psl_sentiment", "sentiment_score"),
    )


__all__ = ["PostSemanticLabel"]
