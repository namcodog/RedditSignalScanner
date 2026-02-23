from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class PostLLMLabel(Base):
    __tablename__ = "post_llm_labels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_id = Column(
        BigInteger,
        ForeignKey("posts_raw.id", ondelete="CASCADE"),
        nullable=False,
    )
    text_norm_hash = Column(String(64))
    llm_version = Column(String(64), nullable=False)
    model_name = Column(String(128))
    prompt_version = Column(String(64))

    value_score = Column(Numeric(4, 2))
    opportunity_score = Column(Numeric(4, 2))
    business_pool = Column(String(10))
    sentiment = Column(Numeric(4, 3))
    purchase_intent_score = Column(Numeric(4, 2))

    tags_analysis = Column(JSONB, nullable=False, default=dict)
    entities_extracted = Column(JSONB, nullable=False, default=list)

    input_chars = Column(Integer)
    output_chars = Column(Integer)
    cost_usd = Column(Numeric(10, 6))

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
        CheckConstraint(
            "business_pool IN ('core','lab','noise')",
            name="ck_post_llm_labels_business_pool",
        ),
        Index("ux_post_llm_labels_post_id", "post_id", unique=True),
        Index("idx_post_llm_labels_created_at", "created_at"),
        Index("idx_post_llm_labels_text_hash", "text_norm_hash"),
    )


class CommentLLMLabel(Base):
    __tablename__ = "comment_llm_labels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    comment_id = Column(
        BigInteger,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    text_norm_hash = Column(String(64))
    llm_version = Column(String(64), nullable=False)
    model_name = Column(String(128))
    prompt_version = Column(String(64))

    value_score = Column(Numeric(4, 2))
    opportunity_score = Column(Numeric(4, 2))
    business_pool = Column(String(10))
    sentiment = Column(Numeric(4, 3))
    purchase_intent_score = Column(Numeric(4, 2))

    tags_analysis = Column(JSONB, nullable=False, default=dict)
    entities_extracted = Column(JSONB, nullable=False, default=list)

    input_chars = Column(Integer)
    output_chars = Column(Integer)
    cost_usd = Column(Numeric(10, 6))

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
        CheckConstraint(
            "business_pool IN ('core','lab','noise')",
            name="ck_comment_llm_labels_business_pool",
        ),
        Index("ux_comment_llm_labels_comment_id", "comment_id", unique=True),
        Index("idx_comment_llm_labels_created_at", "created_at"),
        Index("idx_comment_llm_labels_text_hash", "text_norm_hash"),
    )


__all__ = ["PostLLMLabel", "CommentLLMLabel"]
