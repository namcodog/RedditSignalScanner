"""rename quality_score fields for community tables

Revision ID: 20251116_000033
Revises: 20251116_000032
Create Date: 2025-11-16 00:05:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20251116_000033"
down_revision: Union[str, None] = "20251116_000032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename quality_score columns using safe add-copy-drop strategy."""
    # community_pool.quality_score -> semantic_quality_score
    op.add_column(
        "community_pool",
        sa.Column(
            "semantic_quality_score",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0.50"),
        ),
    )
    op.execute(
        "UPDATE community_pool "
        "SET semantic_quality_score = quality_score "
        "WHERE quality_score IS NOT NULL"
    )
    op.alter_column("community_pool", "semantic_quality_score", server_default=None)
    op.drop_column("community_pool", "quality_score")

    # community_cache.quality_score -> crawl_quality_score
    op.add_column(
        "community_cache",
        sa.Column(
            "crawl_quality_score",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0.50"),
        ),
    )
    op.execute(
        "UPDATE community_cache "
        "SET crawl_quality_score = quality_score "
        "WHERE quality_score IS NOT NULL"
    )
    op.alter_column("community_cache", "crawl_quality_score", server_default=None)
    # Drop old column; existing index on quality_score will be dropped with it
    op.drop_column("community_cache", "quality_score")


def downgrade() -> None:
    """Reverse the rename of quality_score columns."""
    # community_cache.crawl_quality_score -> quality_score
    op.add_column(
        "community_cache",
        sa.Column(
            "quality_score",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0.50"),
        ),
    )
    op.execute(
        "UPDATE community_cache "
        "SET quality_score = crawl_quality_score "
        "WHERE crawl_quality_score IS NOT NULL"
    )
    op.alter_column("community_cache", "quality_score", server_default=None)
    op.drop_column("community_cache", "crawl_quality_score")

    # community_pool.semantic_quality_score -> quality_score
    op.add_column(
        "community_pool",
        sa.Column(
            "quality_score",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0.50"),
        ),
    )
    op.execute(
        "UPDATE community_pool "
        "SET quality_score = semantic_quality_score "
        "WHERE semantic_quality_score IS NOT NULL"
    )
    op.alter_column("community_pool", "quality_score", server_default=None)
    op.drop_column("community_pool", "semantic_quality_score")


