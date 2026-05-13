"""Add tier column to facts_quality_audit.

Revision ID: 20260311_000001
Revises: 20260202_000002, 20260302_000001, 8d5f0f1c2a3b
Create Date: 2026-03-11 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260311_000001"
down_revision: Union[str, tuple[str, ...], None] = (
    "20260202_000002",
    "20260302_000001",
    "8d5f0f1c2a3b",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def _ensure_facts_quality_audit() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("facts_quality_audit"):
        return

    op.create_table(
        "facts_quality_audit",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("config_hash", sa.Text(), nullable=True),
        sa.Column("trend_source", sa.Text(), nullable=True),
        sa.Column("trend_degraded", sa.Boolean(), nullable=True),
        sa.Column("time_window_used", sa.Integer(), nullable=True),
        sa.Column("comments_count", sa.Integer(), nullable=True),
        sa.Column("posts_count", sa.Integer(), nullable=True),
        sa.Column("solutions_count", sa.Integer(), nullable=True),
        sa.Column("community_coverage", sa.Integer(), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=True),
        sa.Column("data_fallback", sa.Boolean(), nullable=True),
        sa.Column("posts_fallback", sa.Boolean(), nullable=True),
        sa.Column("solutions_fallback", sa.Boolean(), nullable=True),
        sa.Column("dynamic_whitelist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dynamic_blacklist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("insufficient_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("idx_facts_quality_created_at", "facts_quality_audit", ["created_at"])


def upgrade() -> None:
    _ensure_facts_quality_audit()
    if not _has_column("facts_quality_audit", "tier"):
        op.add_column("facts_quality_audit", sa.Column("tier", sa.String(length=32), nullable=True))


def downgrade() -> None:
    if _has_column("facts_quality_audit", "tier"):
        op.drop_column("facts_quality_audit", "tier")
