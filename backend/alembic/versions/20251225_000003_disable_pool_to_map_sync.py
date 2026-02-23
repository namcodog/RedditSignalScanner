"""Disable community_pool -> community_category_map sync trigger."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20251225_000003"
down_revision: str | None = "20251225_000002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS sync_category_map_from_pool ON community_pool;")


def downgrade() -> None:
    op.execute(
        """
        CREATE TRIGGER sync_category_map_from_pool
        AFTER INSERT OR UPDATE OF categories ON community_pool
        FOR EACH ROW EXECUTE FUNCTION public.trg_sync_category_map_from_pool()
        """
    )
