"""Phase 6: Add evaluation fields to discovered_communities

Revision ID: 20251206_100001
Revises: 20251206_000001
Create Date: 2025-12-06 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20251206_100001"
down_revision: Union[str, None] = "20251206_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add evaluation fields for Phase 6 Self-Growing Ecosystem."""
    # Add metrics field (JSONB for evaluation data like value_density, subscribers)
    op.add_column(
        "discovered_communities",
        sa.Column("metrics", JSONB, server_default="{}", nullable=False),
    )

    # Add tags field (Array of category tags)
    op.add_column(
        "discovered_communities",
        sa.Column("tags", sa.ARRAY(sa.String), server_default="{}", nullable=False),
    )

    # Add cooldown_until (for rejected communities to skip re-evaluation)
    op.add_column(
        "discovered_communities",
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
    )

    # Add rejection_count (track consecutive rejections for blacklisting)
    op.add_column(
        "discovered_communities",
        sa.Column("rejection_count", sa.Integer, server_default="0", nullable=False),
    )

    # Add index for cooldown queries
    op.create_index(
        "idx_discovered_communities_cooldown",
        "discovered_communities",
        ["cooldown_until"],
        postgresql_where=sa.text("cooldown_until IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove evaluation fields."""
    op.drop_index("idx_discovered_communities_cooldown", table_name="discovered_communities")
    op.drop_column("discovered_communities", "rejection_count")
    op.drop_column("discovered_communities", "cooldown_until")
    op.drop_column("discovered_communities", "tags")
    op.drop_column("discovered_communities", "metrics")
