"""Add dedupe_key to crawler_run_targets for active-target de-duplication.

Revision ID: 20251226_000007
Revises: 20251225_000006
Create Date: 2025-12-26

Why:
- Beat/Planner may run more than once; we must prevent duplicate active targets.
- A partial UNIQUE index on dedupe_key (queued/running) makes it impossible to
  insert duplicate active work for the same logical plan.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251226_000007"
down_revision: str | None = "20251225_000006"
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
    if not _column_exists("crawler_run_targets", "dedupe_key"):
        op.add_column(
            "crawler_run_targets",
            sa.Column("dedupe_key", sa.Text(), nullable=True),
        )

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_crawler_run_targets_dedupe_key_active
            ON crawler_run_targets (dedupe_key)
            WHERE dedupe_key IS NOT NULL
              AND status IN ('queued', 'running')
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS uq_crawler_run_targets_dedupe_key_active"
        )

    if _column_exists("crawler_run_targets", "dedupe_key"):
        op.drop_column("crawler_run_targets", "dedupe_key")
