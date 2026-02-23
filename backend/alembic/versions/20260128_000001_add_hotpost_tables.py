"""Add hotpost tables for boom-post module.

Revision ID: 20260128_000001
Revises: 20260103_000003
Create Date: 2026-01-28
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260128_000001"
down_revision: str | None = "20260103_000003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hotpost_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("time_filter", sa.String(length=10), nullable=False),
        sa.Column("subreddits", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("community_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(length=10), nullable=True),
        sa.Column("from_cache", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("api_calls", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_hotpost_query_created", "hotpost_queries", ["created_at"])
    op.create_index("idx_hotpost_query_mode", "hotpost_queries", ["mode"])
    op.create_index("idx_hotpost_query_user", "hotpost_queries", ["user_id"])

    op.create_table(
        "hotpost_query_evidence_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", sa.BigInteger(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("signal_score", sa.Float(), nullable=True),
        sa.Column("signals", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("top_comment_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["query_id"], ["hotpost_queries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_posts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("query_id", "evidence_id", name="uq_hotpost_query_evidence"),
    )
    op.create_index("idx_map_query", "hotpost_query_evidence_map", ["query_id"])
    op.create_index("idx_map_evidence", "hotpost_query_evidence_map", ["evidence_id"])


def downgrade() -> None:
    op.drop_index("idx_map_evidence", table_name="hotpost_query_evidence_map")
    op.drop_index("idx_map_query", table_name="hotpost_query_evidence_map")
    op.drop_table("hotpost_query_evidence_map")
    op.drop_index("idx_hotpost_query_user", table_name="hotpost_queries")
    op.drop_index("idx_hotpost_query_mode", table_name="hotpost_queries")
    op.drop_index("idx_hotpost_query_created", table_name="hotpost_queries")
    op.drop_table("hotpost_queries")
