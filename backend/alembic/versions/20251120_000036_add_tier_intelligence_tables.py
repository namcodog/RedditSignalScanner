"""Add tier suggestion and audit tables plus community_pool fields.

Revision ID: 20251120_000036
Revises: 20251116_000035
Create Date: 2025-11-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20251120_000036"
down_revision: Union[str, None] = "20251116_000035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tier_suggestions ---
    op.create_table(
        "tier_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("community_name", sa.String(length=100), nullable=False),
        sa.Column("current_tier", sa.String(length=20), nullable=False),
        sa.Column("suggested_tier", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_tier_suggestions_community_name",
        "tier_suggestions",
        ["community_name"],
    )
    op.create_index(
        "ix_tier_suggestions_status",
        "tier_suggestions",
        ["status"],
    )

    # --- tier_audit_logs ---
    op.create_table(
        "tier_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("community_name", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("field_changed", sa.String(length=50), nullable=False),
        sa.Column("from_value", sa.String(length=50), nullable=True),
        sa.Column("to_value", sa.String(length=50), nullable=False),
        sa.Column("changed_by", sa.String(length=100), nullable=False),
        sa.Column("change_source", sa.String(length=20), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("snapshot_before", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("snapshot_after", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("suggestion_id", sa.Integer(), nullable=True),
        sa.Column("is_rolled_back", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_by", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_tier_audit_logs_community_name",
        "tier_audit_logs",
        ["community_name"],
    )
    op.create_index(
        "ix_tier_audit_logs_action",
        "tier_audit_logs",
        ["action"],
    )
    op.create_index(
        "ix_tier_audit_logs_is_rolled_back",
        "tier_audit_logs",
        ["is_rolled_back"],
    )

    # --- community_pool extra fields ---
    op.add_column(
        "community_pool",
        sa.Column(
            "health_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
    )
    op.add_column(
        "community_pool",
        sa.Column(
            "last_evaluated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "community_pool",
        sa.Column(
            "auto_tier_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("community_pool", "auto_tier_enabled")
    op.drop_column("community_pool", "last_evaluated_at")
    op.drop_column("community_pool", "health_status")

    op.drop_index("ix_tier_audit_logs_is_rolled_back", table_name="tier_audit_logs")
    op.drop_index("ix_tier_audit_logs_action", table_name="tier_audit_logs")
    op.drop_index("ix_tier_audit_logs_community_name", table_name="tier_audit_logs")
    op.drop_table("tier_audit_logs")

    op.drop_index("ix_tier_suggestions_status", table_name="tier_suggestions")
    op.drop_index("ix_tier_suggestions_community_name", table_name="tier_suggestions")
    op.drop_table("tier_suggestions")

