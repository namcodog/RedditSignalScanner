"""add llm label tables for posts/comments

Revision ID: 20260202_000001
Revises: 20260128_000001
Create Date: 2026-02-02
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260202_000001"
down_revision: str | None = "20260128_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "post_llm_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("text_norm_hash", sa.String(length=64), nullable=True),
        sa.Column("llm_version", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("value_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("opportunity_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("business_pool", sa.String(length=10), nullable=True),
        sa.Column("sentiment", sa.Numeric(4, 3), nullable=True),
        sa.Column("purchase_intent_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("tags_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("entities_extracted", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("input_chars", sa.Integer(), nullable=True),
        sa.Column("output_chars", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "business_pool IN ('core','lab','noise')",
            name="ck_post_llm_labels_business_pool",
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts_raw.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ux_post_llm_labels_post_id",
        "post_llm_labels",
        ["post_id"],
        unique=True,
    )
    op.create_index(
        "idx_post_llm_labels_created_at",
        "post_llm_labels",
        ["created_at"],
    )
    op.create_index(
        "idx_post_llm_labels_text_hash",
        "post_llm_labels",
        ["text_norm_hash"],
    )

    op.create_table(
        "comment_llm_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("comment_id", sa.BigInteger(), nullable=False),
        sa.Column("text_norm_hash", sa.String(length=64), nullable=True),
        sa.Column("llm_version", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("value_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("opportunity_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("business_pool", sa.String(length=10), nullable=True),
        sa.Column("sentiment", sa.Numeric(4, 3), nullable=True),
        sa.Column("purchase_intent_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("tags_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("entities_extracted", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("input_chars", sa.Integer(), nullable=True),
        sa.Column("output_chars", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "business_pool IN ('core','lab','noise')",
            name="ck_comment_llm_labels_business_pool",
        ),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ux_comment_llm_labels_comment_id",
        "comment_llm_labels",
        ["comment_id"],
        unique=True,
    )
    op.create_index(
        "idx_comment_llm_labels_created_at",
        "comment_llm_labels",
        ["created_at"],
    )
    op.create_index(
        "idx_comment_llm_labels_text_hash",
        "comment_llm_labels",
        ["text_norm_hash"],
    )


def downgrade() -> None:
    op.drop_index("idx_comment_llm_labels_text_hash", table_name="comment_llm_labels")
    op.drop_index("idx_comment_llm_labels_created_at", table_name="comment_llm_labels")
    op.drop_index("ux_comment_llm_labels_comment_id", table_name="comment_llm_labels")
    op.drop_table("comment_llm_labels")

    op.drop_index("idx_post_llm_labels_text_hash", table_name="post_llm_labels")
    op.drop_index("idx_post_llm_labels_created_at", table_name="post_llm_labels")
    op.drop_index("ux_post_llm_labels_post_id", table_name="post_llm_labels")
    op.drop_table("post_llm_labels")
