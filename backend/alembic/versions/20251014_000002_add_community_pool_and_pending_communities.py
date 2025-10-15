"""Add community_pool and pending_communities tables.

Revision ID: 20251014_000002
Revises: 20251010_000001
Create Date: 2025-10-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20251014_000002"
down_revision: Union[str, None] = "20251010_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_pool",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("daily_posts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("avg_comment_length", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("quality_score", sa.Numeric(3, 2), nullable=False, server_default=sa.text("0.50")),
        sa.Column("user_feedback_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("char_length(name) BETWEEN 3 AND 100", name="ck_community_pool_name_len"),
    )

    op.create_index("idx_community_pool_tier", "community_pool", ["tier"])
    op.create_index("idx_community_pool_is_active", "community_pool", ["is_active"])
    op.create_index("idx_community_pool_quality_score", "community_pool", ["quality_score"])

    op.create_table(
        "pending_communities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("discovered_from_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("admin_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.CheckConstraint("char_length(name) BETWEEN 3 AND 100", name="ck_pending_communities_name_len"),
    )

    op.create_index("idx_pending_communities_status", "pending_communities", ["status"])
    op.create_index("idx_pending_communities_discovered_count", "pending_communities", ["discovered_count"])


def downgrade() -> None:
    op.drop_index("idx_pending_communities_discovered_count", table_name="pending_communities")
    op.drop_index("idx_pending_communities_status", table_name="pending_communities")
    op.drop_table("pending_communities")

    op.drop_index("idx_community_pool_quality_score", table_name="community_pool")
    op.drop_index("idx_community_pool_is_active", table_name="community_pool")
    op.drop_index("idx_community_pool_tier", table_name="community_pool")
    op.drop_table("community_pool")

