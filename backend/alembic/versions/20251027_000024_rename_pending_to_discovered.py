"""Rename pending_communities table to discovered_communities.

Revision ID: 20251027_000024
Revises: 20251026_000023
Create Date: 2025-10-27
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


def _rename_constraint(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE constraint_name = '{old}'
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new};
            END IF;
        END
        $$;
        """
    )

revision: str = "20251027_000024"
down_revision: Union[str, None] = "20251026_000023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("pending_communities", "discovered_communities")

    op.execute(
        "ALTER SEQUENCE IF EXISTS pending_communities_id_seq RENAME TO discovered_communities_id_seq"
    )

    op.execute(
        "ALTER INDEX IF EXISTS idx_pending_communities_task_id RENAME TO idx_discovered_communities_task_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_pending_communities_reviewed_by RENAME TO idx_discovered_communities_reviewed_by"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_pending_communities_status RENAME TO idx_discovered_communities_status"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_pending_communities_deleted_at RENAME TO idx_discovered_communities_deleted_at"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_pending_communities_discovered_count RENAME TO idx_discovered_communities_discovered_count"
    )

    _rename_constraint(
        "discovered_communities",
        "ck_pending_communities_name_len",
        "ck_discovered_communities_name_len",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_pending_communities_discovered_from_task_id_tasks",
        "fk_discovered_communities_discovered_from_task_id_tasks",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_pending_communities_reviewed_by",
        "fk_discovered_communities_reviewed_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_pending_communities_created_by",
        "fk_discovered_communities_created_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_pending_communities_updated_by",
        "fk_discovered_communities_updated_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_pending_communities_deleted_by",
        "fk_discovered_communities_deleted_by",
    )


def downgrade() -> None:
    _rename_constraint(
        "discovered_communities",
        "fk_discovered_communities_deleted_by",
        "fk_pending_communities_deleted_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_discovered_communities_updated_by",
        "fk_pending_communities_updated_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_discovered_communities_created_by",
        "fk_pending_communities_created_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_discovered_communities_reviewed_by",
        "fk_pending_communities_reviewed_by",
    )
    _rename_constraint(
        "discovered_communities",
        "fk_discovered_communities_discovered_from_task_id_tasks",
        "fk_pending_communities_discovered_from_task_id_tasks",
    )
    _rename_constraint(
        "discovered_communities",
        "ck_discovered_communities_name_len",
        "ck_pending_communities_name_len",
    )

    op.execute(
        "ALTER INDEX IF EXISTS idx_discovered_communities_deleted_at RENAME TO idx_pending_communities_deleted_at"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_discovered_communities_status RENAME TO idx_pending_communities_status"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_discovered_communities_reviewed_by RENAME TO idx_pending_communities_reviewed_by"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_discovered_communities_task_id RENAME TO idx_pending_communities_task_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS idx_discovered_communities_discovered_count RENAME TO idx_pending_communities_discovered_count"
    )

    op.execute(
        "ALTER SEQUENCE IF EXISTS discovered_communities_id_seq RENAME TO pending_communities_id_seq"
    )

    op.rename_table("discovered_communities", "pending_communities")
