"""Attach posts_raw quarantine trigger used by truth-source tests."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260406_000006"
down_revision: str | None = "20260406_000005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regproc('public.trg_func_auto_score_posts') IS NOT NULL THEN
                DROP TRIGGER IF EXISTS auto_score_posts_raw ON public.posts_raw;
                CREATE TRIGGER auto_score_posts_raw
                BEFORE INSERT OR UPDATE ON public.posts_raw
                FOR EACH ROW
                EXECUTE FUNCTION public.trg_func_auto_score_posts();
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS auto_score_posts_raw ON public.posts_raw")
