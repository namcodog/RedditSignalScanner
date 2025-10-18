"""
Add Phase 3 fields to crawl_metrics: total_new_posts, total_updated_posts, total_duplicates, tier_assignments

Revision ID: 20251018_000011
Revises: 20251017_000010
Create Date: 2025-10-18 19:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251018_000011"
down_revision = "20251017_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("crawl_metrics")}

    to_add = []
    if "total_new_posts" not in cols:
        to_add.append(sa.Column("total_new_posts", sa.Integer(), nullable=False, server_default="0"))
    if "total_updated_posts" not in cols:
        to_add.append(sa.Column("total_updated_posts", sa.Integer(), nullable=False, server_default="0"))
    if "total_duplicates" not in cols:
        to_add.append(sa.Column("total_duplicates", sa.Integer(), nullable=False, server_default="0"))
    if "tier_assignments" not in cols:
        to_add.append(sa.Column("tier_assignments", postgresql.JSON(astext_type=sa.Text()), nullable=True))

    for col in to_add:
        op.add_column("crawl_metrics", col)

    # drop server defaults to rely on app-level defaults
    if to_add:
        with op.batch_alter_table("crawl_metrics") as batch_op:
            if "total_new_posts" not in cols:
                batch_op.alter_column("total_new_posts", server_default=None)
            if "total_updated_posts" not in cols:
                batch_op.alter_column("total_updated_posts", server_default=None)
            if "total_duplicates" not in cols:
                batch_op.alter_column("total_duplicates", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("crawl_metrics")}
    with op.batch_alter_table("crawl_metrics") as batch_op:
        if "total_new_posts" in cols:
            batch_op.drop_column("total_new_posts")
        if "total_updated_posts" in cols:
            batch_op.drop_column("total_updated_posts")
        if "total_duplicates" in cols:
            batch_op.drop_column("total_duplicates")
        if "tier_assignments" in cols:
            batch_op.drop_column("tier_assignments")

