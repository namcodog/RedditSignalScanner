"""Add crawler_run_targets table + community_run_id tracking columns (safe / additive).

Revision ID: 20251218_000001
Revises: 20251217_000007
Create Date: 2025-12-18

Why:
- We already generate a parent crawl_run_id per scheduled "整轮抓取" (A).
- We also need a child community_run_id per subreddit within the same run (B),
  so we can audit/rollback/diagnose at community granularity without polluting
  the main tables with batch/page IDs.

Safety:
- Only adds nullable columns to big tables.
- Uses partial indexes CONCURRENTLY to minimize locks and keep indexes small
  when historical rows are NULL.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20251218_000001"
down_revision: str | None = "20251217_000007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crawler_run_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subreddit", sa.Text(), nullable=False),
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
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message_short", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawler_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_crawler_run_targets"),
        sa.UniqueConstraint(
            "crawl_run_id",
            "subreddit",
            name="uq_crawler_run_targets_run_subreddit",
        ),
    )
    op.create_index(
        "idx_crawler_run_targets_crawl_run_id",
        "crawler_run_targets",
        ["crawl_run_id"],
        unique=False,
    )
    op.create_index(
        "idx_crawler_run_targets_subreddit",
        "crawler_run_targets",
        ["subreddit"],
        unique=False,
    )
    op.create_index(
        "idx_crawler_run_targets_status",
        "crawler_run_targets",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_crawler_run_targets_started_at",
        "crawler_run_targets",
        ["started_at"],
        unique=False,
    )

    op.add_column(
        "posts_raw",
        sa.Column("community_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "comments",
        sa.Column("community_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_raw_community_run_id
            ON posts_raw (community_run_id)
            WHERE community_run_id IS NOT NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_community_run_id
            ON comments (community_run_id)
            WHERE community_run_id IS NOT NULL
            """
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_comments_community_run_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_posts_raw_community_run_id")

    op.drop_column("comments", "community_run_id")
    op.drop_column("posts_raw", "community_run_id")

    op.drop_index("idx_crawler_run_targets_started_at", table_name="crawler_run_targets")
    op.drop_index("idx_crawler_run_targets_status", table_name="crawler_run_targets")
    op.drop_index("idx_crawler_run_targets_subreddit", table_name="crawler_run_targets")
    op.drop_index(
        "idx_crawler_run_targets_crawl_run_id", table_name="crawler_run_targets"
    )
    op.drop_table("crawler_run_targets")

