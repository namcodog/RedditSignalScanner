"""Enable auto_tier_enabled by default."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251222_000004"
down_revision: str | None = "20251222_000003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "community_pool",
        "auto_tier_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )
    op.execute(
        "UPDATE community_pool SET auto_tier_enabled = true "
        "WHERE auto_tier_enabled = false"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE community_pool SET auto_tier_enabled = false "
        "WHERE auto_tier_enabled = true"
    )
    op.alter_column(
        "community_pool",
        "auto_tier_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
