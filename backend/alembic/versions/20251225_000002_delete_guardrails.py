"""Add delete guardrails for critical tables."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20251225_000002"
down_revision: str | None = "20251225_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_GUARDED_TABLES: list[tuple[str, str]] = [
    ("posts_raw", "guard_delete_posts_raw"),
    ("posts_hot", "guard_delete_posts_hot"),
    ("comments", "guard_delete_comments"),
    ("content_labels", "guard_delete_content_labels"),
    ("content_entities", "guard_delete_content_entities"),
    ("facts_snapshots", "guard_delete_facts_snapshots"),
    ("facts_run_logs", "guard_delete_facts_run_logs"),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.guard_delete()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Skip guardrails in test databases to avoid blocking fixtures.
            IF current_database() LIKE '%_test' THEN
                RETURN OLD;
            END IF;

            IF current_setting('app.allow_delete', true) IS DISTINCT FROM '1' THEN
                RAISE EXCEPTION 'delete blocked: app.allow_delete not set';
            END IF;

            RETURN OLD;
        END;
        $$;
        """
    )

    for table, trigger_name in _GUARDED_TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = '{trigger_name}'
                ) THEN
                    CREATE TRIGGER {trigger_name}
                    BEFORE DELETE ON {table}
                    FOR EACH ROW EXECUTE FUNCTION public.guard_delete();
                END IF;
            END
            $$;
            """
        )


def downgrade() -> None:
    for table, trigger_name in _GUARDED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table};")

    op.execute("DROP FUNCTION IF EXISTS public.guard_delete();")
