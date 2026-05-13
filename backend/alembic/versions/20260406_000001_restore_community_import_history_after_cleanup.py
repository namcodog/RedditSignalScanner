"""restore community import history after cleanup branch"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260406_000001"
down_revision = "20260405_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT to_regclass('public.community_import_history')")
    ).scalar()
    if exists:
        return

    op.create_table(
        "community_import_history",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dry_run",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary_preview", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_community_import_history_uploaded_by",
        "community_import_history",
        ["uploaded_by_user_id"],
    )
    op.create_index(
        "idx_community_import_history_created_at",
        "community_import_history",
        ["created_at"],
    )


def downgrade() -> None:
    # The table is an active admin audit contract; this repair migration must not
    # delete audit history when rolling back unrelated later schema changes.
    pass
