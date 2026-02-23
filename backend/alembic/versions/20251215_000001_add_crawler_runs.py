"""Add crawler_runs table and run tracking columns (safe / non-destructive)

Revision ID: 20251215_000001
Revises: 20251214_000005
Create Date: 2025-12-15 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251215_000001'
down_revision: Union[str, None] = '20251214_000005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: This migration is designed to be "safe by default":
    # - Only adds nullable columns (no backfill, no NOT NULL)
    # - Avoids heavyweight validation work on large tables
    # - Builds indexes CONCURRENTLY to minimize table locks
    #
    # IMPORTANT: We intentionally do NOT add FK constraints here.
    # Adding FK constraints can introduce new write-path failures if any writer
    # forgets to ensure the parent crawler_runs row exists.

    # 1) Create crawler_runs table (id must be provided by application code).
    op.create_table(
        "crawler_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crawler_runs"),
    )
    op.create_index("idx_crawler_runs_status", "crawler_runs", ["status"], unique=False)
    op.create_index(
        "idx_crawler_runs_started_at", "crawler_runs", ["started_at"], unique=False
    )

    # 2) Add crawl_run_id columns (nullable) to hot/cold stores.
    op.add_column(
        "posts_raw",
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "comments",
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "crawl_metrics",
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # 3) Add partial indexes CONCURRENTLY (small when most rows are NULL).
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_raw_crawl_run_id
            ON posts_raw (crawl_run_id)
            WHERE crawl_run_id IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_crawl_run_id
            ON comments (crawl_run_id)
            WHERE crawl_run_id IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_crawl_metrics_crawl_run_id
            ON crawl_metrics (crawl_run_id)
            WHERE crawl_run_id IS NOT NULL
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_crawl_metrics_crawl_run_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_comments_crawl_run_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_posts_raw_crawl_run_id")

    op.drop_column("crawl_metrics", "crawl_run_id")
    op.drop_column("comments", "crawl_run_id")
    op.drop_column("posts_raw", "crawl_run_id")

    op.drop_index("idx_crawler_runs_started_at", table_name="crawler_runs")
    op.drop_index("idx_crawler_runs_status", table_name="crawler_runs")
    op.drop_table("crawler_runs")
