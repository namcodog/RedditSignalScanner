"""Add crawler_run_targets plan identity fields + community_cache waterlines (safe / additive).

Revision ID: 20251218_000002
Revises: 20251218_000001
Create Date: 2025-12-18

Why:
- We reuse `crawler_run_targets.config` as the canonical CrawlPlan payload (Phase-1收口).
- Backfill needs multiple plans per (crawl_run_id, subreddit) via time-slicing.
- A stable `idempotency_key` prevents duplicate plans and enables audit-friendly retries.
- `community_cache` needs `backfill_floor` + `last_attempt_at` to prevent A/B schedule fighting.

Safety:
- Only adds nullable columns.
- Replaces the old UNIQUE (crawl_run_id, subreddit) constraint with a partial UNIQUE index
  on (crawl_run_id, idempotency_key) created CONCURRENTLY.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251218_000002"
down_revision: str | None = "20251218_000001"
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
    # 1) community_cache: add backfill & attempt waterlines
    if not _column_exists("community_cache", "backfill_floor"):
        op.add_column(
            "community_cache",
            sa.Column("backfill_floor", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("community_cache", "last_attempt_at"):
        op.add_column(
            "community_cache",
            sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        )

    # 2) crawler_run_targets: add plan identity fields
    if not _column_exists("crawler_run_targets", "plan_kind"):
        op.add_column(
            "crawler_run_targets",
            sa.Column("plan_kind", sa.String(length=32), nullable=True),
        )
    if not _column_exists("crawler_run_targets", "idempotency_key"):
        op.add_column(
            "crawler_run_targets",
            sa.Column("idempotency_key", sa.Text(), nullable=True),
        )
    if not _column_exists("crawler_run_targets", "idempotency_key_human"):
        op.add_column(
            "crawler_run_targets",
            sa.Column("idempotency_key_human", sa.Text(), nullable=True),
        )

    # 3) Drop legacy UNIQUE (crawl_run_id, subreddit) so backfill slices can coexist.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_crawler_run_targets_run_subreddit'
            ) THEN
                ALTER TABLE crawler_run_targets
                DROP CONSTRAINT uq_crawler_run_targets_run_subreddit;
            END IF;
        END $$;
        """
    )

    # 4) New plan identity: UNIQUE (crawl_run_id, idempotency_key) for non-null keys.
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_crawler_run_targets_run_idempotency_key
            ON crawler_run_targets (crawl_run_id, idempotency_key)
            WHERE idempotency_key IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_crawler_run_targets_plan_kind
            ON crawler_run_targets (plan_kind)
            WHERE plan_kind IS NOT NULL
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS uq_crawler_run_targets_run_idempotency_key"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_crawler_run_targets_plan_kind"
        )

    # Re-add legacy UNIQUE constraint (best-effort; may fail if duplicates exist).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_crawler_run_targets_run_subreddit'
            ) THEN
                ALTER TABLE crawler_run_targets
                ADD CONSTRAINT uq_crawler_run_targets_run_subreddit
                UNIQUE (crawl_run_id, subreddit);
            END IF;
        END $$;
        """
    )

    if _column_exists("crawler_run_targets", "idempotency_key_human"):
        op.drop_column("crawler_run_targets", "idempotency_key_human")
    if _column_exists("crawler_run_targets", "idempotency_key"):
        op.drop_column("crawler_run_targets", "idempotency_key")
    if _column_exists("crawler_run_targets", "plan_kind"):
        op.drop_column("crawler_run_targets", "plan_kind")

    if _column_exists("community_cache", "last_attempt_at"):
        op.drop_column("community_cache", "last_attempt_at")
    if _column_exists("community_cache", "backfill_floor"):
        op.drop_column("community_cache", "backfill_floor")

