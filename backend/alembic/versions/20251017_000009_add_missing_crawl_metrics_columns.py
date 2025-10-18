"""
Add missing columns to crawl_metrics: successful_crawls, empty_crawls, failed_crawls, avg_latency_seconds

Revision ID: 20251017_000009
Revises: 20251017_000008
Create Date: 2025-10-17 15:27:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251017_000009"
down_revision = "20251017_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("crawl_metrics")}

    to_add = []
    if "successful_crawls" not in cols:
        to_add.append(sa.Column("successful_crawls", sa.Integer(), nullable=False, server_default="0"))
    if "empty_crawls" not in cols:
        to_add.append(sa.Column("empty_crawls", sa.Integer(), nullable=False, server_default="0"))
    if "failed_crawls" not in cols:
        to_add.append(sa.Column("failed_crawls", sa.Integer(), nullable=False, server_default="0"))
    if "avg_latency_seconds" not in cols:
        to_add.append(sa.Column("avg_latency_seconds", sa.Numeric(7, 2), nullable=False, server_default="0.00"))

    for col in to_add:
        op.add_column("crawl_metrics", col)

    # drop server defaults to rely on app-level defaults
    if to_add:
        with op.batch_alter_table("crawl_metrics") as batch_op:
            if "successful_crawls" not in cols:
                batch_op.alter_column("successful_crawls", server_default=None)
            if "empty_crawls" not in cols:
                batch_op.alter_column("empty_crawls", server_default=None)
            if "failed_crawls" not in cols:
                batch_op.alter_column("failed_crawls", server_default=None)
            if "avg_latency_seconds" not in cols:
                batch_op.alter_column("avg_latency_seconds", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("crawl_metrics")}
    with op.batch_alter_table("crawl_metrics") as batch_op:
        if "successful_crawls" in cols:
            batch_op.drop_column("successful_crawls")
        if "empty_crawls" in cols:
            batch_op.drop_column("empty_crawls")
        if "failed_crawls" in cols:
            batch_op.drop_column("failed_crawls")
        if "avg_latency_seconds" in cols:
            batch_op.drop_column("avg_latency_seconds")

