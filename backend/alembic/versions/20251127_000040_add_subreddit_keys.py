"""Add canonical subreddit key columns for consistent joins.

Revision ID: 20251127_000040
Revises: 20251116_000034
Create Date: 2025-11-27
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251127_000040"
down_revision: Union[str, None] = "20251116_000034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add computed columns without r/ prefix for stable subreddit joins.

    - community_pool.name_key
    - community_cache.community_key
    """
    op.add_column(
        "community_pool",
        sa.Column(
            "name_key",
            sa.String(length=100),
            sa.Computed("lower(regexp_replace(name, '^r/', ''))", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("idx_community_pool_name_key", "community_pool", ["name_key"], unique=False)

    op.add_column(
        "community_cache",
        sa.Column(
            "community_key",
            sa.String(length=100),
            sa.Computed("lower(regexp_replace(community_name, '^r/', ''))", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("idx_cache_community_key", "community_cache", ["community_key"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_cache_community_key", table_name="community_cache")
    op.drop_column("community_cache", "community_key")

    op.drop_index("idx_community_pool_name_key", table_name="community_pool")
    op.drop_column("community_pool", "name_key")
