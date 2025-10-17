"""
Create crawl_metrics table for monitoring (T1.3)

Revision ID: 20251016_000006
Revises: 20251016_000005
Create Date: 2025-10-16 23:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251016_000006"
down_revision = "20251016_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("metric_hour", sa.Integer(), nullable=False),
        sa.Column("cache_hit_rate", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("valid_posts_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_metrics_metric_date", "crawl_metrics", ["metric_date"], unique=False)
    op.create_index("idx_metrics_metric_hour", "crawl_metrics", ["metric_hour"], unique=False)

    # Remove server defaults to rely on application-level defaults
    with op.batch_alter_table("crawl_metrics") as batch_op:
        batch_op.alter_column("cache_hit_rate", server_default=None)
        batch_op.alter_column("valid_posts_24h", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_metrics_metric_hour", table_name="crawl_metrics")
    op.drop_index("idx_metrics_metric_date", table_name="crawl_metrics")
    op.drop_table("crawl_metrics")

