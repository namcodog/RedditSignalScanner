"""Add community import history table and priority column.

Revision ID: 20251015_000003
Revises: 20251014_000002
Create Date: 2025-10-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20251015_000003"
down_revision: Union[str, None] = "20251014_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if priority column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('community_pool')]

    if 'priority' not in columns:
        op.add_column(
            "community_pool",
            sa.Column("priority", sa.String(length=20), nullable=False, server_default=sa.text("'medium'")),
        )

    # Check if table already exists
    tables = inspector.get_table_names()

    if 'community_import_history' not in tables:
        op.create_table(
            "community_import_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("uploaded_by", sa.String(length=255), nullable=False),
            sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("valid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("imported_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "error_details",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "summary_preview",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )

        op.create_index(
            "idx_community_import_history_created",
            "community_import_history",
            ["created_at"],
        )


def downgrade() -> None:
    op.drop_index("idx_community_import_history_created", table_name="community_import_history")
    op.drop_table("community_import_history")
    op.drop_column("community_pool", "priority")
