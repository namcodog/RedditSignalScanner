"""add tiered TTL strategy for comments

Revision ID: 20251116_000035
Revises: 20251116_000034
Create Date: 2025-11-16 00:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20251116_000035"
down_revision: Union[str, None] = "20251116_000034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply tiered TTL to comments and add trigger."""
    # 更新现有评论的 expires_at（仅处理 currently NULL 的记录）
    op.execute(
        """
        UPDATE comments
        SET expires_at = CASE
            WHEN score > 100 OR awards_count > 5 THEN created_utc + interval '365 days'
            WHEN score > 10 THEN created_utc + interval '180 days'
            ELSE created_utc + interval '30 days'
        END
        WHERE expires_at IS NULL
        """
    )

    # 创建触发器函数
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_comment_expires_at()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.expires_at IS NULL THEN
                NEW.expires_at := CASE
                    WHEN NEW.score > 100 OR NEW.awards_count > 5 THEN NEW.created_utc + interval '365 days'
                    WHEN NEW.score > 10 THEN NEW.created_utc + interval '180 days'
                    ELSE NEW.created_utc + interval '30 days'
                END;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # 确保 BEFORE INSERT 触发器存在（单条语句执行）
    op.execute("DROP TRIGGER IF EXISTS trg_set_comment_expires ON comments;")
    op.execute(
        """
        CREATE TRIGGER trg_set_comment_expires
        BEFORE INSERT ON comments
        FOR EACH ROW
        EXECUTE FUNCTION set_comment_expires_at();
        """
    )


def downgrade() -> None:
    """Drop tiered TTL trigger and function.

    为避免在漂移环境中误删 expires_at 字段，本迁移的降级不回滚字段值，只移除触发器逻辑。
    """
    op.execute("DROP TRIGGER IF EXISTS trg_set_comment_expires ON comments;")
    op.execute("DROP FUNCTION IF EXISTS set_comment_expires_at();")

