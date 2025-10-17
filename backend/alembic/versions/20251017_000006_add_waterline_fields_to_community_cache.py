"""
Add waterline fields to community_cache: last_seen_post_id, last_seen_created_at, total_posts_fetched, dedup_rate

Revision ID: 20251017_000006
Revises: 20251017_000009
Create Date: 2025-10-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251017_000006"
down_revision: Union[str, None] = "20251017_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Waterline fields for incremental crawler/bookmarking
    op.add_column(
        "community_cache",
        sa.Column("last_seen_post_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "community_cache",
        sa.Column("last_seen_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_cache",
        sa.Column(
            "total_posts_fetched",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "community_cache",
        sa.Column("dedup_rate", sa.Numeric(5, 2), nullable=True),
    )

    # Optional: drop server_default to keep application-side defaults later
    with op.batch_alter_table("community_cache") as batch_op:
        batch_op.alter_column("total_posts_fetched", server_default=None)


def downgrade() -> None:
    op.drop_column("community_cache", "dedup_rate")
    op.drop_column("community_cache", "total_posts_fetched")
    op.drop_column("community_cache", "last_seen_created_at")
    op.drop_column("community_cache", "last_seen_post_id")

