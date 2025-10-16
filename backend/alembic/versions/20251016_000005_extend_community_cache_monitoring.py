"""
Extend community_cache monitoring fields: empty_hit, success_hit, failure_hit, avg_valid_posts, quality_tier

Revision ID: 20251016_000005
Revises: 20251015_000004
Create Date: 2025-10-16 23:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251016_000005"
down_revision = "20251015_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("community_cache", sa.Column("empty_hit", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("community_cache", sa.Column("success_hit", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("community_cache", sa.Column("failure_hit", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("community_cache", sa.Column("avg_valid_posts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("community_cache", sa.Column("quality_tier", sa.String(length=20), nullable=False, server_default="medium"))
    # Optional helpful indexes
    op.create_index("idx_cache_quality_tier", "community_cache", ["quality_tier"], unique=False)

    # Drop server_default to keep future inserts using application defaults
    with op.batch_alter_table("community_cache") as batch_op:
        batch_op.alter_column("empty_hit", server_default=None)
        batch_op.alter_column("success_hit", server_default=None)
        batch_op.alter_column("failure_hit", server_default=None)
        batch_op.alter_column("avg_valid_posts", server_default=None)
        batch_op.alter_column("quality_tier", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_cache_quality_tier", table_name="community_cache")
    op.drop_column("community_cache", "quality_tier")
    op.drop_column("community_cache", "avg_valid_posts")
    op.drop_column("community_cache", "failure_hit")
    op.drop_column("community_cache", "success_hit")
    op.drop_column("community_cache", "empty_hit")

