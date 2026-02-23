"""Drop discovered_communities -> community_pool foreign key.

Revision ID: 20260202_000002
Revises: 20260202_000001
Create Date: 2026-02-02
"""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260202_000002"
down_revision: str | None = "20260202_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_discovered_to_pool",
        "discovered_communities",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "fk_discovered_to_pool",
        "discovered_communities",
        "community_pool",
        ["name"],
        ["name"],
        ondelete="SET NULL",
    )
