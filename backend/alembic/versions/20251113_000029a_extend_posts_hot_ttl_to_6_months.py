"""extend posts_hot TTL to 6 months

Revision ID: 20251113_000029a
Revises: 20251112_000028
Create Date: 2025-11-13 12:45:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251113_000029a"
down_revision = "20251112_000028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修改 posts_hot 表的 expires_at 默认值从 24 小时改为 6 个月（180 天）
    op.execute(
        """
        ALTER TABLE posts_hot 
        ALTER COLUMN expires_at 
        SET DEFAULT (now() + INTERVAL '180 days')
        """
    )
    
    # 更新现有记录的 expires_at（可选，如果想让现有数据也延长 TTL）
    op.execute(
        """
        UPDATE posts_hot 
        SET expires_at = cached_at + INTERVAL '180 days'
        WHERE expires_at < (cached_at + INTERVAL '180 days')
        """
    )


def downgrade() -> None:
    # 恢复为 24 小时
    op.execute(
        """
        ALTER TABLE posts_hot 
        ALTER COLUMN expires_at 
        SET DEFAULT (now() + INTERVAL '24 hours')
        """
    )

