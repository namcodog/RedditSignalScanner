"""add audit_level to tasks

Revision ID: 20251217_000006
Revises: 20251217_000005
Create Date: 2025-12-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251217_000006"
down_revision = "20251217_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("audit_level", sa.String(length=20), nullable=True))

    # Backfill: default rule (no historic explicit override exists)
    op.execute(
        """
        UPDATE tasks
        SET audit_level = CASE
            WHEN topic_profile_id IS NOT NULL AND topic_profile_id <> '' THEN 'gold'
            ELSE 'lab'
        END
        WHERE audit_level IS NULL
        """
    )

    op.alter_column(
        "tasks",
        "audit_level",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=sa.text("'lab'"),
    )

    op.create_check_constraint(
        "ck_tasks_valid_audit_level",
        "tasks",
        "audit_level IN ('gold', 'lab', 'noise')",
    )
    op.create_index(
        "ix_tasks_audit_level",
        "tasks",
        ["audit_level"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_audit_level", table_name="tasks")
    op.drop_constraint("ck_tasks_valid_audit_level", "tasks", type_="check")
    op.drop_column("tasks", "audit_level")

