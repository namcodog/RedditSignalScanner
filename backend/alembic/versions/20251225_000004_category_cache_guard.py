"""Guard community_pool.categories updates and allow map sync."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20251225_000004"
down_revision: str | None = "20251225_000003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.guard_community_pool_categories_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF current_setting('app.allow_category_cache_update', true) = '1' THEN
                RETURN NEW;
            END IF;

            INSERT INTO data_audit_events
                (event_type, target_type, target_id, old_value, new_value, reason, source_component)
            VALUES
                (
                    'blocked_write',
                    'community_pool',
                    NEW.id::text,
                    COALESCE(OLD.categories, '{}'::jsonb),
                    COALESCE(NEW.categories, '{}'::jsonb),
                    'direct_categories_update_blocked',
                    'guard_community_pool_categories_update'
                );

            RAISE EXCEPTION 'direct update to community_pool.categories blocked';
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS guard_community_pool_categories_update ON community_pool;")
    op.execute(
        """
        CREATE TRIGGER guard_community_pool_categories_update
        BEFORE UPDATE OF categories ON community_pool
        FOR EACH ROW EXECUTE FUNCTION public.guard_community_pool_categories_update()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sync_community_pool_categories_from_map(pool_id integer)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            keys text[];
        BEGIN
            IF pool_id IS NULL THEN
                RETURN;
            END IF;

            PERFORM set_config('app.allow_category_cache_update', '1', true);

            SELECT array_agg(category_key ORDER BY is_primary DESC, category_key) INTO keys
            FROM community_category_map
            WHERE community_id = pool_id;

            IF keys IS NULL THEN
                UPDATE community_pool
                SET categories = '[]'::jsonb
                WHERE id = pool_id;
            ELSE
                UPDATE community_pool
                SET categories = to_jsonb(keys)
                WHERE id = pool_id;
            END IF;
        END;
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF current_database() NOT LIKE '%_test'
               AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rss_app') THEN
                REVOKE UPDATE (categories) ON community_pool FROM rss_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS guard_community_pool_categories_update ON community_pool;")
    op.execute("DROP FUNCTION IF EXISTS public.guard_community_pool_categories_update;")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sync_community_pool_categories_from_map(pool_id integer)
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        DECLARE
            keys text[];
        BEGIN
            IF pool_id IS NULL THEN
                RETURN;
            END IF;

            SELECT array_agg(category_key ORDER BY is_primary DESC, category_key) INTO keys
            FROM community_category_map
            WHERE community_id = pool_id;

            IF keys IS NULL THEN
                UPDATE community_pool
                SET categories = '[]'::jsonb
                WHERE id = pool_id;
            ELSE
                UPDATE community_pool
                SET categories = to_jsonb(keys)
                WHERE id = pool_id;
            END IF;
        END;
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF current_database() NOT LIKE '%_test'
               AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rss_app') THEN
                GRANT UPDATE (categories) ON community_pool TO rss_app;
            END IF;
        END
        $$;
        """
    )
