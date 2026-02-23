"""Fix community_pool id sequence drift.

Revision ID: 20251217_000003
Revises: 20251217_000002
Create Date: 2025-12-17

Why:
- Some environments have had manual inserts specifying `community_pool.id`,
  causing `community_pool_id_seq` to lag behind and generate duplicate IDs.
- This migration repairs the sequence WITHOUT touching existing table data.
- Safety: never decreases the sequence, so we avoid ID reuse.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251217_000003"
down_revision: str | None = "20251217_000002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    seq_name = bind.execute(
        sa.text("SELECT pg_get_serial_sequence('public.community_pool', 'id')")
    ).scalar_one_or_none()
    if not seq_name:
        return

    max_id = int(
        bind.execute(
            sa.text("SELECT COALESCE(MAX(id), 0) FROM public.community_pool")
        ).scalar_one()
    )

    schema, sequence = _split_qualified_name(str(seq_name))
    last_value, is_called = bind.execute(
        sa.text(f'SELECT last_value, is_called FROM "{schema}"."{sequence}"')
    ).one()
    last_value_int = int(last_value)
    is_called_bool = bool(is_called)

    current_next = last_value_int + 1 if is_called_bool else last_value_int
    target_next = max(max_id + 1, current_next)

    bind.execute(
        sa.text("SELECT setval(CAST(:seq AS regclass), :target_next, false)"),
        {"seq": str(seq_name), "target_next": target_next},
    )


def downgrade() -> None:
    # Non-reversible maintenance migration: sequence drift is fixed forward only.
    return


def _split_qualified_name(value: str) -> tuple[str, str]:
    raw = value.strip()
    if "." not in raw:
        return "public", raw.strip('"')
    left, right = raw.split(".", 1)
    return left.strip('"'), right.strip('"')
