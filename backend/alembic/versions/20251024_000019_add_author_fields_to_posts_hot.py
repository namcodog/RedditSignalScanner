"""add author fields to posts_hot"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251024_000019"
down_revision = "20251024_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 检查 posts_hot 表是否存在
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'posts_hot'
            )
            """
        )
    )
    posts_hot_exists = result.scalar()

    if not posts_hot_exists:
        return

    # 检查列是否已存在
    result = conn.execute(
        sa.text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'posts_hot'
            AND column_name IN ('author_id', 'author_name')
            """
        )
    )
    existing_columns = {row[0] for row in result}

    # 只添加不存在的列
    if "author_id" not in existing_columns:
        op.add_column(
            "posts_hot",
            sa.Column("author_id", sa.String(length=100), nullable=True),
        )

    if "author_name" not in existing_columns:
        op.add_column(
            "posts_hot",
            sa.Column("author_name", sa.String(length=100), nullable=True),
        )

    # 更新数据
    op.execute(
        """
        UPDATE posts_hot
        SET
            author_name = COALESCE(author_name, metadata->>'author'),
            author_id = COALESCE(author_id, metadata->>'author')
        WHERE metadata IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("posts_hot", "author_name")
    op.drop_column("posts_hot", "author_id")
