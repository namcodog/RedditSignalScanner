"""Add backfill status + checkpoint fields to community_cache.

Revision ID: 20251225_000006
Revises: 20251225_000005
Create Date: 2025-12-25

Why:
- Provide a single source of truth for backfill progress (DONE_12M/DONE_CAPPED).
- Persist cursor checkpoints for resume without re-scanning pages.
- Keep planner logic simple and auditable.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251225_000006"
down_revision: str | None = "20251225_000005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name=:table
              AND column_name=:column
            LIMIT 1
            """
        ),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _column_exists("community_cache", "backfill_status"):
        op.add_column(
            "community_cache",
            sa.Column(
                "backfill_status",
                sa.String(length=20),
                nullable=True,
                server_default=sa.text("'NEEDS'"),
            ),
        )
    if not _column_exists("community_cache", "coverage_months"):
        op.add_column(
            "community_cache",
            sa.Column(
                "coverage_months",
                sa.SmallInteger(),
                nullable=True,
                server_default=sa.text("0"),
            ),
        )
    if not _column_exists("community_cache", "sample_posts"):
        op.add_column(
            "community_cache",
            sa.Column(
                "sample_posts",
                sa.Integer(),
                nullable=True,
                server_default=sa.text("0"),
            ),
        )
    if not _column_exists("community_cache", "sample_comments"):
        op.add_column(
            "community_cache",
            sa.Column(
                "sample_comments",
                sa.Integer(),
                nullable=True,
                server_default=sa.text("0"),
            ),
        )
    if not _column_exists("community_cache", "backfill_capped"):
        op.add_column(
            "community_cache",
            sa.Column(
                "backfill_capped",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
            ),
        )
    if not _column_exists("community_cache", "backfill_cursor"):
        op.add_column(
            "community_cache",
            sa.Column("backfill_cursor", sa.Text(), nullable=True),
        )
    if not _column_exists("community_cache", "backfill_cursor_created_at"):
        op.add_column(
            "community_cache",
            sa.Column("backfill_cursor_created_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("community_cache", "backfill_updated_at"):
        op.add_column(
            "community_cache",
            sa.Column("backfill_updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_community_cache_backfill_status
            ON community_cache (backfill_status)
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_community_cache_backfill_status"
        )

    if _column_exists("community_cache", "backfill_updated_at"):
        op.drop_column("community_cache", "backfill_updated_at")
    if _column_exists("community_cache", "backfill_cursor_created_at"):
        op.drop_column("community_cache", "backfill_cursor_created_at")
    if _column_exists("community_cache", "backfill_cursor"):
        op.drop_column("community_cache", "backfill_cursor")
    if _column_exists("community_cache", "backfill_capped"):
        op.drop_column("community_cache", "backfill_capped")
    if _column_exists("community_cache", "sample_comments"):
        op.drop_column("community_cache", "sample_comments")
    if _column_exists("community_cache", "sample_posts"):
        op.drop_column("community_cache", "sample_posts")
    if _column_exists("community_cache", "coverage_months"):
        op.drop_column("community_cache", "coverage_months")
    if _column_exists("community_cache", "backfill_status"):
        op.drop_column("community_cache", "backfill_status")
