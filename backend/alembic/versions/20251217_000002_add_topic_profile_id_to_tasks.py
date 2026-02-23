"""add topic_profile_id to tasks

Revision ID: 20251217_000002
Revises: 20251217_000001
Create Date: 2025-12-17 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251217_000002"
down_revision = "20251217_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("topic_profile_id", sa.String(length=100), nullable=True),
    )
    op.create_check_constraint(
        "ck_tasks_valid_topic_profile_id",
        "tasks",
        "(topic_profile_id IS NULL) OR (topic_profile_id <> '')",
    )
    op.create_index(
        "ix_tasks_topic_profile_id",
        "tasks",
        ["topic_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_topic_profile_id", table_name="tasks")
    op.drop_constraint("ck_tasks_valid_topic_profile_id", "tasks", type_="check")
    op.drop_column("tasks", "topic_profile_id")

