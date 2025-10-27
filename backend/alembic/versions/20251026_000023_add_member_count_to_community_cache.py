"""Add member_count to community_cache for dynamic member tracking.

Revision ID: 20251026_000023
Revises: 20251024_000022
Create Date: 2025-10-26

This migration adds a member_count field to the community_cache table
to support dynamic tracking of community member counts from Reddit API.
This replaces the hardcoded DEFAULT_COMMUNITY_MEMBERS dictionary.

Related to: P1-5 (硬编码的社区成员数)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20251026_000023"
down_revision: Union[str, None] = "20251024_000022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add member_count column to community_cache table."""
    # Add member_count column (nullable to allow gradual population)
    op.add_column(
        "community_cache",
        sa.Column(
            "member_count",
            sa.Integer(),
            nullable=True,
            comment="Number of members in the community (from Reddit API)",
        ),
    )
    
    # Add index for efficient queries
    op.create_index(
        "idx_community_cache_member_count",
        "community_cache",
        ["member_count"],
        unique=False,
    )
    
    # Add check constraint to ensure non-negative values
    op.create_check_constraint(
        "ck_community_cache_member_count_non_negative",
        "community_cache",
        "member_count IS NULL OR member_count >= 0",
    )


def downgrade() -> None:
    """Remove member_count column from community_cache table."""
    # Drop check constraint
    op.drop_constraint(
        "ck_community_cache_member_count_non_negative",
        "community_cache",
        type_="check",
    )
    
    # Drop index
    op.drop_index(
        "idx_community_cache_member_count",
        table_name="community_cache",
    )
    
    # Drop column
    op.drop_column("community_cache", "member_count")

