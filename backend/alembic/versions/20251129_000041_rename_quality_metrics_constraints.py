"""Rename garbled quality_metrics constraint names to readable ones.

Revision ID: 20251129_000041
Revises: 20251127_000040, 20251125_add_created_at
Create Date: 2025-11-29 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251129_000041"
down_revision: Union[str, tuple[str, ...], None] = (
    "20251127_000040",
    "20251125_add_created_at",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RENAME_MAP: tuple[tuple[str, str], ...] = (
    (
        "ck_quality_metrics_ck_quality_metrics_collection_succes_7b01",
        "ck_quality_metrics_collection_rate_range",
    ),
    (
        "ck_quality_metrics_ck_quality_metrics_deduplication_rate_range",
        "ck_quality_metrics_dedup_rate_range",
    ),
    (
        "ck_quality_metrics_ck_quality_metrics_p95_gte_p50",
        "ck_quality_metrics_p95_gte_p50",
    ),
    (
        "ck_quality_metrics_ck_quality_metrics_processing_time_p_fc40",
        "ck_quality_metrics_p50_positive",
    ),
    (
        "ck_quality_metrics_ck_quality_metrics_processing_time_p_ac65",
        "ck_quality_metrics_p95_positive",
    ),
)


def _rename_constraint(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = '{table}' AND c.conname = '{old}'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = '{table}' AND c.conname = '{new}'
            ) THEN
                EXECUTE 'ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}';
            END IF;
        END;
        $$;
        """
    )


def upgrade() -> None:
    for old, new in RENAME_MAP:
        _rename_constraint("quality_metrics", old, new)


def downgrade() -> None:
    for old, new in reversed(RENAME_MAP):
        _rename_constraint("quality_metrics", new, old)
