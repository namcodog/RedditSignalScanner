"""
Add unique constraint and missing fields to crawl_metrics (T1.4)

Revision ID: 20251019_000013
Revises: 20251018_000012
Create Date: 2025-10-19 03:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251019_000013"
down_revision = "20251018_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加唯一约束（metric_date, metric_hour）
    # 使用 batch_alter_table 来检查约束是否已存在
    from sqlalchemy import inspect
    from sqlalchemy.engine import reflection

    conn = op.get_bind()
    inspector = inspect(conn)

    # 检查约束是否已存在
    constraints = inspector.get_unique_constraints("crawl_metrics")
    constraint_names = [c["name"] for c in constraints]

    if "uq_crawl_metrics_date_hour" not in constraint_names:
        op.create_unique_constraint(
            "uq_crawl_metrics_date_hour",
            "crawl_metrics",
            ["metric_date", "metric_hour"]
        )


def downgrade() -> None:
    op.drop_constraint("uq_crawl_metrics_date_hour", "crawl_metrics", type_="unique")

