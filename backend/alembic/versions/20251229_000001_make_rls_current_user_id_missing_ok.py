"""Make RLS current_user_id missing_ok to avoid 500.

Revision ID: 20251229_000001
Revises: 20251226_000009
Create Date: 2025-12-29

Why:
- RLS policy on analyses currently uses current_setting('app.current_user_id') without missing_ok,
  which raises "unrecognized configuration parameter" and crashes the API when the session GUC
  isn't injected.
- This migration makes the policy deny-by-default (returns no rows) instead of crashing.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20251229_000001"
down_revision: str | None = "20251226_000009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    # Replace policy with missing_ok=true to avoid crashing when the GUC is absent.
    bind.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname='public'
                      AND tablename='analyses'
                      AND policyname='policy_analyses_tenant_isolation'
                ) THEN
                    EXECUTE 'DROP POLICY policy_analyses_tenant_isolation ON public.analyses';
                END IF;
            END $$;
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE POLICY policy_analyses_tenant_isolation
            ON public.analyses
            USING (
                task_id IN (
                    SELECT tasks.id
                    FROM public.tasks
                    WHERE tasks.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            );
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname='public'
                      AND tablename='analyses'
                      AND policyname='policy_analyses_tenant_isolation'
                ) THEN
                    EXECUTE 'DROP POLICY policy_analyses_tenant_isolation ON public.analyses';
                END IF;
            END $$;
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE POLICY policy_analyses_tenant_isolation
            ON public.analyses
            USING (
                task_id IN (
                    SELECT tasks.id
                    FROM public.tasks
                    WHERE tasks.user_id = (current_setting('app.current_user_id'::text))::uuid
                )
            );
            """
        )
    )
