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
    conn = op.get_bind()

    # 检查 community_import_history 表是否存在
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
        # 删除 community_import_history 表及其索引
        op.execute("DROP INDEX IF EXISTS idx_community_import_history_created_at")
        op.execute("DROP INDEX IF EXISTS idx_community_import_history_uploaded_by")
        op.execute("DROP TABLE IF EXISTS community_import_history")

    # 检查 community_watermarks 表是否存在
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'community_watermarks'
            )
            """
        )
    )
    if result.scalar():
        # 删除 community_watermarks 表
        op.execute("DROP TABLE IF EXISTS community_watermarks")


def downgrade() -> None:
    """
    恢复已删除的表（如果需要回滚）
    注意：此函数设计为幂等，可以安全地多次执行
    """
    conn = op.get_bind()

    # 检查 community_watermarks 表是否不存在，才创建
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'community_watermarks'
            )
            """
        )
    )
    if not result.scalar():
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

    # 检查 community_import_history 表是否不存在，才创建
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

        # 恢复索引（只在表被创建时）
        op.create_index("idx_community_import_history_uploaded_by", "community_import_history", ["uploaded_by_user_id"])
        op.create_index("idx_community_import_history_created_at", "community_import_history", ["created_at"])
