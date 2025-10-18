"""Add community_name format constraint to require r/ prefix.

Revision ID: 20251018_000012
Revises: 20251018_000011
Create Date: 2025-10-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251018_000012"
down_revision: Union[str, None] = "20251018_000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add CHECK constraint to enforce community_name format: r/[a-zA-Z0-9_]+

    Based on exa-code best practices:
    - PostgreSQL regex operator: ~
    - Pattern: ^r/[a-zA-Z0-9_]+$ (must start with r/ followed by alphanumeric + underscore)
    - Case-sensitive matching (Reddit community names are case-sensitive)

    Migration steps:
    1. Update existing data to add r/ prefix if missing
    2. Add CHECK constraints to enforce format
    """
    # Step 1: Update existing data in community_pool
    op.execute("""
        UPDATE community_pool
        SET name = 'r/' || name
        WHERE name !~ '^r/'
    """)

    # Step 2: Update existing data in pending_communities
    op.execute("""
        UPDATE pending_communities
        SET name = 'r/' || name
        WHERE name !~ '^r/'
    """)

    # Step 3: Update existing data in community_cache
    op.execute("""
        UPDATE community_cache
        SET community_name = 'r/' || community_name
        WHERE community_name !~ '^r/'
    """)

    # Step 4: Add constraint to community_pool table
    op.create_check_constraint(
        "ck_community_pool_name_format",
        "community_pool",
        "name ~ '^r/[a-zA-Z0-9_]+$'",
    )

    # Step 5: Add constraint to pending_communities table
    op.create_check_constraint(
        "ck_pending_communities_name_format",
        "pending_communities",
        "name ~ '^r/[a-zA-Z0-9_]+$'",
    )

    # Step 6: Add constraint to community_cache table
    op.create_check_constraint(
        "ck_community_cache_name_format",
        "community_cache",
        "community_name ~ '^r/[a-zA-Z0-9_]+$'",
    )


def downgrade() -> None:
    """
    Remove the format constraints and revert data to original format.

    Rollback steps:
    1. Drop CHECK constraints
    2. Remove r/ prefix from existing data
    """
    # Step 1: Drop constraints
    op.drop_constraint("ck_community_cache_name_format", "community_cache", type_="check")
    op.drop_constraint("ck_pending_communities_name_format", "pending_communities", type_="check")
    op.drop_constraint("ck_community_pool_name_format", "community_pool", type_="check")

    # Step 2: Revert data in community_pool
    op.execute("""
        UPDATE community_pool
        SET name = substring(name FROM 3)
        WHERE name ~ '^r/'
    """)

    # Step 3: Revert data in pending_communities
    op.execute("""
        UPDATE pending_communities
        SET name = substring(name FROM 3)
        WHERE name ~ '^r/'
    """)

    # Step 4: Revert data in community_cache
    op.execute("""
        UPDATE community_cache
        SET community_name = substring(community_name FROM 3)
        WHERE community_name ~ '^r/'
    """)

