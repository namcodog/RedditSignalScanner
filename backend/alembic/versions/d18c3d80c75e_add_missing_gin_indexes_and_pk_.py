"""add_missing_gin_indexes_and_pk_adjustments"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d18c3d80c75e"
down_revision = 'aef64335bd34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add GIN indexes for JSONB columns (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_pool_categories_gin
        ON community_pool USING gin (categories)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_pool_keywords_gin
        ON community_pool USING gin (description_keywords)
    """)

    # Add GIN index for posts_hot metadata (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_posts_hot_metadata_gin
        ON posts_hot USING gin (metadata)
    """)

    # Add missing indexes for pending_communities (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_task_id
        ON pending_communities (discovered_from_task_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_reviewed_by
        ON pending_communities (reviewed_by)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_communities_status
        ON pending_communities (status)
    """)

    # Add missing indexes for community_import_history (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_import_history_uploaded_by
        ON community_import_history (uploaded_by_user_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_community_import_history_created_at
        ON community_import_history (created_at)
    """)


def downgrade() -> None:
    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS idx_community_pool_categories_gin")
    op.execute("DROP INDEX IF EXISTS idx_community_pool_keywords_gin")
    op.execute("DROP INDEX IF EXISTS idx_posts_hot_metadata_gin")

    # Drop other indexes
    op.execute("DROP INDEX IF EXISTS idx_pending_communities_task_id")
    op.execute("DROP INDEX IF EXISTS idx_pending_communities_reviewed_by")
    op.execute("DROP INDEX IF EXISTS idx_pending_communities_status")
    op.execute("DROP INDEX IF EXISTS idx_community_import_history_uploaded_by")
    op.execute("DROP INDEX IF EXISTS idx_community_import_history_created_at")
