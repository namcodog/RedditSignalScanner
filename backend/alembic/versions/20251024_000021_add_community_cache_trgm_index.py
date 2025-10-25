"""add trigram index for community cache name search"""

from __future__ import annotations

from alembic import op


revision = "20251024_000021"
down_revision = "20251024_000020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "idx_community_cache_name_trgm",
        "community_cache",
        ["community_name"],
        postgresql_using="gin",
        postgresql_ops={"community_name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "idx_community_cache_name_trgm",
        table_name="community_cache",
    )
