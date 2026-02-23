"""add expires_at to comments and index

Revision ID: 20251113_000029
Revises: 20251113_000029a
Create Date: 2025-11-13 16:10:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251113_000029"
down_revision = "20251113_000029a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add expires_at to comments for TTL-based cleanup
    op.add_column(
        "comments",
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    try:
        op.create_index("idx_comments_expires_at", "comments", ["expires_at"]) 
    except Exception:
        # index may already exist in some environments
        pass


def downgrade() -> None:
    try:
        op.drop_index("idx_comments_expires_at", table_name="comments")
    except Exception:
        pass
    op.drop_column("comments", "expires_at")

