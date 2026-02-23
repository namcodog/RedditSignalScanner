"""add authors and subreddit_snapshots tables

Revision ID: 20251112_000026
Revises: 20251112_000025
Create Date: 2025-11-13 00:45:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251112_000026"
down_revision = "20251112_000025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # authors
    op.create_table(
        "authors",
        sa.Column("author_id", sa.String(length=100), primary_key=True),
        sa.Column("author_name", sa.String(length=100), nullable=True),
        sa.Column("created_utc", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "first_seen_at_global",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # subreddit_snapshots
    op.create_table(
        "subreddit_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column(
            "captured_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("subscribers", sa.String(length=32), nullable=True),
        sa.Column("active_user_count", sa.String(length=32), nullable=True),
        sa.Column("rules_text", sa.Text(), nullable=True),
        sa.Column("over18", sa.Boolean(), nullable=True),
    )
    op.create_index(
        "idx_subreddit_snapshots_time", "subreddit_snapshots", ["subreddit", "captured_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_subreddit_snapshots_time", table_name="subreddit_snapshots")
    op.drop_table("subreddit_snapshots")
    op.drop_table("authors")

