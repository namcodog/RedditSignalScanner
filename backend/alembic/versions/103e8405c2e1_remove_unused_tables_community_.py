"""remove_unused_tables_community_watermarks_and_import_history"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "103e8405c2e1"
down_revision = '20251024_000021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    删除未使用的孤岛表:
    - community_watermarks: 0行数据,代码中无引用
    - community_import_history: 0行数据,代码中无引用
    """
    # 删除 community_import_history 表及其索引
    op.drop_index("idx_community_import_history_created_at", table_name="community_import_history")
    op.drop_index("idx_community_import_history_uploaded_by", table_name="community_import_history")
    op.drop_table("community_import_history")

    # 删除 community_watermarks 表
    op.drop_table("community_watermarks")


def downgrade() -> None:
    """
    恢复已删除的表（如果需要回滚）
    """
    # 恢复 community_watermarks 表
    op.create_table(
        "community_watermarks",
        sa.Column("community_name", sa.String(100), primary_key=True),
        sa.Column("last_seen_post_id", sa.String(100), nullable=True),
        sa.Column("last_seen_created_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("total_posts_fetched", sa.Integer, default=0),
        sa.Column("dedup_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("last_crawled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB, nullable=True),
    )

    # 恢复 community_import_history 表
    op.create_table(
        "community_import_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("uploaded_by", sa.String(255), nullable=False),
        sa.Column("uploaded_by_user_id", sa.dialects.postgresql.UUID, nullable=True),
        sa.Column("dry_run", sa.Boolean, nullable=False, default=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_rows", sa.Integer, nullable=False, default=0),
        sa.Column("valid_rows", sa.Integer, nullable=False, default=0),
        sa.Column("invalid_rows", sa.Integer, nullable=False, default=0),
        sa.Column("duplicate_rows", sa.Integer, nullable=False, default=0),
        sa.Column("imported_rows", sa.Integer, nullable=False, default=0),
        sa.Column("error_details", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("summary_preview", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
    )

    # 恢复索引
    op.create_index("idx_community_import_history_uploaded_by", "community_import_history", ["uploaded_by_user_id"])
    op.create_index("idx_community_import_history_created_at", "community_import_history", ["created_at"])
