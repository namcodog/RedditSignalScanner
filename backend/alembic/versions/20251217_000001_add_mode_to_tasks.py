"""add mode to tasks

Revision ID: 20251217_000001
Revises: 20251215_000001
Create Date: 2025-12-17 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251217_000001"
down_revision = "20251215_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("mode", sa.String(length=50), nullable=True))
    op.execute("UPDATE tasks SET mode='market_insight' WHERE mode IS NULL")
    op.alter_column(
        "tasks",
        "mode",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=sa.text("'market_insight'"),
    )
    op.create_check_constraint(
        "ck_tasks_valid_mode",
        "tasks",
        "mode IN ('market_insight', 'operations')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tasks_valid_mode", "tasks", type_="check")
    op.drop_column("tasks", "mode")

