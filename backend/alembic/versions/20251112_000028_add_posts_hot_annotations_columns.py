"""add content_labels and entities columns to posts_hot (nullable JSONB)

Revision ID: 20251112_000028
Revises: 20251112_000027
Create Date: 2025-11-13 01:18:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20251112_000028"
down_revision = "20251112_000027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts_hot",
        sa.Column("content_labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "posts_hot",
        sa.Column("entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("posts_hot", "entities")
    op.drop_column("posts_hot", "content_labels")

