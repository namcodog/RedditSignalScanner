"""add moderation_score to subreddit_snapshots

Revision ID: 20251112_000027
Revises: 20251112_000026
Create Date: 2025-11-13 01:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251112_000027"
down_revision = "20251112_000026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subreddit_snapshots", sa.Column("moderation_score", sa.Integer(), nullable=True)
    )
    op.create_index(
        "idx_subreddit_snapshots_subreddit", "subreddit_snapshots", ["subreddit"]
    )


def downgrade() -> None:
    op.drop_index("idx_subreddit_snapshots_subreddit", table_name="subreddit_snapshots")
    op.drop_column("subreddit_snapshots", "moderation_score")

