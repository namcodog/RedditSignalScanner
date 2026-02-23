"""Add created_at to content_labels and content_entities; widen category/aspect.

Revision ID: 20251125_add_created_at
Revises: 20251120_000036
Create Date: 2025-11-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20251125_add_created_at"
down_revision = "20251120_000036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # created_at with default now(), nullable=False
    op.add_column(
        "content_labels",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "content_entities",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    # widen category/aspect to reduce future truncation risk
    op.alter_column("content_labels", "category", type_=sa.String(length=64))
    op.alter_column("content_labels", "aspect", type_=sa.String(length=64))


def downgrade() -> None:
    op.alter_column("content_labels", "aspect", type_=sa.String(length=12))
    op.alter_column("content_labels", "category", type_=sa.String(length=8))
    op.drop_column("content_entities", "created_at")
    op.drop_column("content_labels", "created_at")
