"""Add warmup period fields to pending_communities and community_cache.

Revision ID: 20251015_000004
Revises: 20251015_000003
Create Date: 2025-10-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20251015_000004"
down_revision: Union[str, None] = "20251015_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add fields to pending_communities for warmup period tracking
    op.add_column(
        "pending_communities",
        sa.Column("discovered_from_task_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pending_communities",
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        "fk_pending_communities_task_id",
        "pending_communities",
        "tasks",
        ["discovered_from_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pending_communities_reviewed_by",
        "pending_communities",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Add fields to community_cache for adaptive crawler
    op.add_column(
        "community_cache",
        sa.Column("crawl_frequency_hours", sa.Integer(), nullable=False, server_default=sa.text("2")),
    )
    op.add_column(
        "community_cache",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    
    # Add indexes for performance
    op.create_index(
        "idx_pending_communities_task_id",
        "pending_communities",
        ["discovered_from_task_id"],
    )
    op.create_index(
        "idx_community_cache_is_active",
        "community_cache",
        ["is_active"],
    )
    op.create_index(
        "idx_community_cache_crawl_frequency",
        "community_cache",
        ["crawl_frequency_hours"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_community_cache_crawl_frequency", table_name="community_cache")
    op.drop_index("idx_community_cache_is_active", table_name="community_cache")
    op.drop_index("idx_pending_communities_task_id", table_name="pending_communities")
    
    # Drop columns from community_cache
    op.drop_column("community_cache", "is_active")
    op.drop_column("community_cache", "crawl_frequency_hours")
    
    # Drop foreign keys and columns from pending_communities
    op.drop_constraint("fk_pending_communities_reviewed_by", "pending_communities", type_="foreignkey")
    op.drop_constraint("fk_pending_communities_task_id", "pending_communities", type_="foreignkey")
    op.drop_column("pending_communities", "reviewed_by")
    op.drop_column("pending_communities", "discovered_from_task_id")

