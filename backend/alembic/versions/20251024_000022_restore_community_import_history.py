"""Restore community import history table for admin Excel uploads."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251024_000022"
down_revision = "20251024_000021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    创建 community_import_history 表（幂等）
    """
    conn = op.get_bind()

    # 检查表是否已存在
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'community_import_history'
            )
            """
        )
    )

    if not result.scalar():
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
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
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
    """
    删除 community_import_history 表（幂等）
    """
    conn = op.get_bind()

    # 检查表是否存在
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'community_import_history'
            )
            """
        )
    )

    if result.scalar():
        # 使用 IF EXISTS 确保幂等性
        op.execute("DROP INDEX IF EXISTS idx_community_import_history_created_at")
        op.execute("DROP INDEX IF EXISTS idx_community_import_history_uploaded_by")
        op.drop_table("community_import_history")
