"""
Add total_communities column to crawl_metrics if missing (hotfix for T1.3)

Revision ID: 20251017_000008
Revises: 20251017_000007
Create Date: 2025-10-17 15:25:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251017_000008"
down_revision = "20251017_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("crawl_metrics")}
    if "total_communities" not in cols:
        op.add_column(
            "crawl_metrics",
            sa.Column("total_communities", sa.Integer(), nullable=False, server_default="0"),
        )
        # remove server default to rely on app-level defaults
        with op.batch_alter_table("crawl_metrics") as batch_op:
            batch_op.alter_column("total_communities", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("crawl_metrics")}
    if "total_communities" in cols:
        with op.batch_alter_table("crawl_metrics") as batch_op:
            batch_op.drop_column("total_communities")

