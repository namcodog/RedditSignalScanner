"""Add evidence_posts table for probe audit (safe / additive).

Revision ID: 20251218_000003
Revises: 20251218_000002
Create Date: 2025-12-18

Why:
- Probe/search/hot needs a durable, auditable "evidence posts" log.
- Idempotent de-dup prevents repeated runs from blowing up the DB.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20251218_000003"
down_revision: str | None = "20251218_000002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("probe_source", sa.String(length=20), nullable=False),
        sa.Column("source_query", sa.Text(), nullable=True),
        sa.Column("source_query_hash", sa.String(length=64), nullable=False),
        sa.Column("source_post_id", sa.String(length=100), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("num_comments", sa.Integer(), server_default="0", nullable=False),
        sa.Column("post_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["crawl_run_id"], ["crawler_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"], ["crawler_run_targets.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_posts"),
        sa.UniqueConstraint(
            "probe_source",
            "source_query_hash",
            "source_post_id",
            name="uq_evidence_posts_probe_query_post",
        ),
    )

    op.create_index(
        "idx_evidence_posts_probe_query",
        "evidence_posts",
        ["probe_source", "source_query_hash"],
        unique=False,
    )
    op.create_index(
        "idx_evidence_posts_subreddit_created",
        "evidence_posts",
        ["subreddit", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_evidence_posts_target_id",
        "evidence_posts",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        "idx_evidence_posts_crawl_run_id",
        "evidence_posts",
        ["crawl_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_evidence_posts_crawl_run_id", table_name="evidence_posts")
    op.drop_index("idx_evidence_posts_target_id", table_name="evidence_posts")
    op.drop_index("idx_evidence_posts_subreddit_created", table_name="evidence_posts")
    op.drop_index("idx_evidence_posts_probe_query", table_name="evidence_posts")
    op.drop_table("evidence_posts")
