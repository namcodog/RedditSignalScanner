"""add foreign keys between community tables

Revision ID: 20251116_000034
Revises: 20251116_000033
Create Date: 2025-11-16 00:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20251116_000034"
down_revision: Union[str, None] = "20251116_000033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Clean orphan records and add foreign key constraints."""
    # 清理 community_cache 孤儿记录
    op.execute(
        """
        DELETE FROM community_cache
        WHERE community_name NOT IN (SELECT name FROM community_pool)
        """
    )

    # 清理 discovered_communities 孤儿记录
    op.execute(
        """
        DELETE FROM discovered_communities
        WHERE name NOT IN (SELECT name FROM community_pool)
        """
    )

    # 添加外键约束
    op.create_foreign_key(
        "fk_community_cache_pool",
        "community_cache",
        "community_pool",
        ["community_name"],
        ["name"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_discovered_to_pool",
        "discovered_communities",
        "community_pool",
        ["name"],
        ["name"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop foreign key constraints between community tables."""
    op.drop_constraint(
        "fk_discovered_to_pool",
        "discovered_communities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_community_cache_pool",
        "community_cache",
        type_="foreignkey",
    )


