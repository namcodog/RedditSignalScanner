"""add comments captured_at index and maintenance_audit table

Revision ID: 20251114_000030
Revises: 20251113_000029
Create Date: 2025-11-14 18:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251114_000030"
down_revision = "20251113_000029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safe index on captured_at to support TTL cleanup
    try:
        op.create_index("idx_comments_captured_at", "comments", ["captured_at"])  # type: ignore[arg-type]
    except Exception:
        pass

    # Maintenance audit table for destructive operations
    op.create_table(
        "maintenance_audit",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("triggered_by", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("affected_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sample_ids", postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    try:
        op.create_index("idx_maintenance_audit_task", "maintenance_audit", ["task_name"])  # type: ignore[arg-type]
        op.create_index("idx_maintenance_audit_started", "maintenance_audit", ["started_at"])  # type: ignore[arg-type]
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("idx_maintenance_audit_started", table_name="maintenance_audit")
        op.drop_index("idx_maintenance_audit_task", table_name="maintenance_audit")
    except Exception:
        pass
    op.drop_table("maintenance_audit")
    try:
        op.drop_index("idx_comments_captured_at", table_name="comments")
    except Exception:
        pass

