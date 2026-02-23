"""Add missing scoring fields to posts_raw (safe / additive).

Revision ID: 20251218_000005
Revises: 20251218_000004
Create Date: 2025-12-22
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251218_000005"
down_revision: str | None = "20251218_000004"
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
    if not _column_exists("posts_raw", "community_id"):
        op.add_column(
            "posts_raw",
            sa.Column("community_id", sa.Integer(), nullable=True),
        )
    if not _column_exists("posts_raw", "score_source"):
        op.add_column(
            "posts_raw",
            sa.Column("score_source", sa.String(length=50), nullable=True),
        )
    if not _column_exists("posts_raw", "score_version"):
        op.add_column(
            "posts_raw",
            sa.Column(
                "score_version",
                sa.Integer(),
                nullable=True,
                server_default=sa.text("1"),
            ),
        )


def downgrade() -> None:
    if _column_exists("posts_raw", "score_version"):
        op.drop_column("posts_raw", "score_version")
    if _column_exists("posts_raw", "score_source"):
        op.drop_column("posts_raw", "score_source")
    if _column_exists("posts_raw", "community_id"):
        op.drop_column("posts_raw", "community_id")
