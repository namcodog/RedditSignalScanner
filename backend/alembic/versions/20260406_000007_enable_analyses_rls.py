"""Enable RLS enforcement for analyses."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260406_000007"
down_revision: str | None = "20260406_000006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE public.analyses DISABLE ROW LEVEL SECURITY")
