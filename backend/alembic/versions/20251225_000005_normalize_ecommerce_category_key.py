"""Normalize Ecommerce_Business category key and alias legacy name."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20251225_000005"
down_revision: str | None = "20251225_000004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO business_categories (key, display_name, description, is_active)
        VALUES ('Ecommerce_Business', 'Ecommerce Business', 'Ecommerce operations & business', true)
        ON CONFLICT (key) DO NOTHING;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sync_community_category_map_from_pool(pool_id integer)
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            raw jsonb;
            keys text[];
            filtered text[];
            inserted_count integer := 0;
            idx integer := 1;
            item text;
        BEGIN
            IF pool_id IS NULL THEN
                RETURN 0;
            END IF;

            SELECT categories INTO raw
            FROM community_pool
            WHERE id = pool_id;

            keys := public.community_category_keys_from_jsonb(raw);

            IF keys IS NULL OR array_length(keys, 1) IS NULL THEN
                DELETE FROM community_category_map WHERE community_id = pool_id;
                RETURN 0;
            END IF;

            SELECT array_agg(k ORDER BY k) INTO filtered
            FROM (
                SELECT DISTINCT
                    CASE
                        WHEN k = 'E-commerce_Ops' THEN 'Ecommerce_Business'
                        ELSE k
                    END AS k
                FROM unnest(keys) AS k
                WHERE k IS NOT NULL
                  AND k <> ''
                  AND EXISTS (
                      SELECT 1
                      FROM business_categories bc
                      WHERE bc.key = CASE
                          WHEN k = 'E-commerce_Ops' THEN 'Ecommerce_Business'
                          ELSE k
                      END
                        AND bc.is_active = true
                  )
            ) AS uniq;

            DELETE FROM community_category_map WHERE community_id = pool_id;

            IF filtered IS NULL OR array_length(filtered, 1) IS NULL THEN
                RETURN 0;
            END IF;

            FOREACH item IN ARRAY filtered LOOP
                INSERT INTO community_category_map (community_id, category_key, is_primary)
                VALUES (pool_id, item, idx = 1)
                ON CONFLICT (community_id, category_key) DO NOTHING;
                inserted_count := inserted_count + 1;
                idx := idx + 1;
            END LOOP;

            RETURN inserted_count;
        END;
        $$;
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

            SELECT array_agg(
                CASE
                    WHEN category_key = 'E-commerce_Ops' THEN 'Ecommerce_Business'
                    ELSE category_key
                END
                ORDER BY is_primary DESC,
                         CASE
                             WHEN category_key = 'E-commerce_Ops' THEN 'Ecommerce_Business'
                             ELSE category_key
                         END
            ) INTO keys
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
        UPDATE community_category_map
        SET category_key = 'Ecommerce_Business'
        WHERE category_key = 'E-commerce_Ops'
          AND NOT EXISTS (
              SELECT 1
              FROM community_category_map m2
              WHERE m2.community_id = community_category_map.community_id
                AND m2.category_key = 'Ecommerce_Business'
          );
        """
    )
    op.execute(
        """
        DELETE FROM community_category_map
        WHERE category_key = 'E-commerce_Ops'
          AND EXISTS (
              SELECT 1
              FROM community_category_map m2
              WHERE m2.community_id = community_category_map.community_id
                AND m2.category_key = 'Ecommerce_Business'
          );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sync_community_category_map_from_pool(pool_id integer)
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            raw jsonb;
            keys text[];
            filtered text[];
            inserted_count integer := 0;
            idx integer := 1;
            item text;
        BEGIN
            IF pool_id IS NULL THEN
                RETURN 0;
            END IF;

            SELECT categories INTO raw
            FROM community_pool
            WHERE id = pool_id;

            keys := public.community_category_keys_from_jsonb(raw);

            IF keys IS NULL OR array_length(keys, 1) IS NULL THEN
                DELETE FROM community_category_map WHERE community_id = pool_id;
                RETURN 0;
            END IF;

            SELECT array_agg(k ORDER BY k) INTO filtered
            FROM (
                SELECT DISTINCT k
                FROM unnest(keys) AS k
                WHERE k IS NOT NULL
                  AND k <> ''
                  AND EXISTS (
                      SELECT 1
                      FROM business_categories bc
                      WHERE bc.key = k AND bc.is_active = true
                  )
            ) AS uniq;

            DELETE FROM community_category_map WHERE community_id = pool_id;

            IF filtered IS NULL OR array_length(filtered, 1) IS NULL THEN
                RETURN 0;
            END IF;

            FOREACH item IN ARRAY filtered LOOP
                INSERT INTO community_category_map (community_id, category_key, is_primary)
                VALUES (pool_id, item, idx = 1)
                ON CONFLICT (community_id, category_key) DO NOTHING;
                inserted_count := inserted_count + 1;
                idx := idx + 1;
            END LOOP;

            RETURN inserted_count;
        END;
        $$;
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
