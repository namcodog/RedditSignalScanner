"""Add value_score to posts_raw (safe / additive).

Revision ID: 20251218_000004
Revises: 20251218_000003
Create Date: 2025-12-18
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251218_000004"
down_revision: str | None = "20251218_000003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    try:
        result = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=:table AND column_name=:column
                LIMIT 1
                """
            ),
            {"table": table, "column": column},
        )
        return result.scalar() is not None
    except Exception:
        return False


def upgrade() -> None:
    if not _column_exists("posts_raw", "value_score"):
        op.add_column(
            "posts_raw",
            sa.Column("value_score", sa.SmallInteger(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("posts_raw", "value_score"):
        op.drop_column("posts_raw", "value_score")
