"""Add tier column to facts_quality_audit.

Revision ID: 20260311_000001
Revises: 20260202_000002, 20260302_000001, 8d5f0f1c2a3b
Create Date: 2026-03-11 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260311_000001"
down_revision: Union[str, tuple[str, ...], None] = (
    "20260202_000002",
    "20260302_000001",
    "8d5f0f1c2a3b",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    if not _has_column("facts_quality_audit", "tier"):
        op.add_column("facts_quality_audit", sa.Column("tier", sa.String(length=32), nullable=True))


def downgrade() -> None:
    if _has_column("facts_quality_audit", "tier"):
        op.drop_column("facts_quality_audit", "tier")
