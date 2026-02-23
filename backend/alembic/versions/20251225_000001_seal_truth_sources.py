"""Seal SSOT constraints and audit anchors for DB."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251225_000001"
down_revision: str | None = "20251223_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO business_categories (key, display_name, description)
            VALUES ('AI_Workflow', 'AI Workflow', 'AI workflow & automation stack')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT community_id,
                   category_key,
                   row_number() OVER (
                       PARTITION BY community_id
                       ORDER BY created_at ASC, category_key ASC
                   ) AS rn
            FROM community_category_map
            WHERE is_primary = true
        )
        UPDATE community_category_map
        SET is_primary = false
        WHERE (community_id, category_key) IN (
            SELECT community_id, category_key
            FROM ranked
            WHERE rn > 1
        )
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_community_category_primary
        ON community_category_map (community_id)
        WHERE is_primary = true
        """
    )

    op.add_column(
        "post_semantic_labels",
        sa.Column(
            "rule_version",
            sa.String(length=50),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
    )
    op.add_column(
        "post_semantic_labels",
        sa.Column(
            "llm_version",
            sa.String(length=50),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_posts_raw_community_id_not_null'
            ) THEN
                ALTER TABLE posts_raw
                    ADD CONSTRAINT ck_posts_raw_community_id_not_null
                    CHECK (community_id IS NOT NULL) NOT VALID;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_posts_raw_community'
            ) THEN
                ALTER TABLE posts_raw
                    ADD CONSTRAINT fk_posts_raw_community
                    FOREIGN KEY (community_id)
                    REFERENCES community_pool(id)
                    NOT VALID;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY source, source_post_id
                       ORDER BY valid_from DESC, id DESC
                   ) AS rn
            FROM posts_raw
            WHERE is_current = true
        )
        UPDATE posts_raw
        SET is_current = false
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_posts_raw_current
        ON posts_raw (source, source_post_id)
        WHERE is_current = true
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.community_category_keys_from_jsonb(raw jsonb)
        RETURNS text[]
        LANGUAGE plpgsql
        AS $$
        DECLARE
            keys text[];
        BEGIN
            IF raw IS NULL THEN
                RETURN ARRAY[]::text[];
            END IF;

            IF jsonb_typeof(raw) = 'array' THEN
                SELECT array_agg(value) INTO keys
                FROM jsonb_array_elements_text(raw) AS value;
                RETURN COALESCE(keys, ARRAY[]::text[]);
            END IF;

            IF jsonb_typeof(raw) = 'object' THEN
                IF raw ? 'categories' AND jsonb_typeof(raw->'categories') = 'array' THEN
                    SELECT array_agg(value) INTO keys
                    FROM jsonb_array_elements_text(raw->'categories') AS value;
                    RETURN COALESCE(keys, ARRAY[]::text[]);
                ELSIF raw ? 'primary' AND jsonb_typeof(raw->'primary') = 'array' THEN
                    SELECT array_agg(value) INTO keys
                    FROM jsonb_array_elements_text(raw->'primary') AS value;
                    RETURN COALESCE(keys, ARRAY[]::text[]);
                ELSE
                    SELECT array_agg(key) INTO keys
                    FROM jsonb_object_keys(raw) AS key;
                    RETURN COALESCE(keys, ARRAY[]::text[]);
                END IF;
            END IF;

            RETURN ARRAY[]::text[];
        END;
        $$;
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
        CREATE OR REPLACE FUNCTION public.trg_sync_category_map_from_pool()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF pg_trigger_depth() > 1 THEN
                RETURN NEW;
            END IF;
            PERFORM public.sync_community_category_map_from_pool(NEW.id);
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS sync_category_map_from_pool ON community_pool;")
    op.execute(
        """
        CREATE TRIGGER sync_category_map_from_pool
        AFTER INSERT OR UPDATE OF categories ON community_pool
        FOR EACH ROW EXECUTE FUNCTION public.trg_sync_category_map_from_pool()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.trg_sync_pool_categories_from_map()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_id integer;
        BEGIN
            IF pg_trigger_depth() > 1 THEN
                RETURN NULL;
            END IF;
            target_id := COALESCE(NEW.community_id, OLD.community_id);
            PERFORM public.sync_community_pool_categories_from_map(target_id);
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS sync_pool_categories_from_map ON community_category_map;")
    op.execute(
        """
        CREATE TRIGGER sync_pool_categories_from_map
        AFTER INSERT OR UPDATE OR DELETE ON community_category_map
        FOR EACH ROW EXECUTE FUNCTION public.trg_sync_pool_categories_from_map()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.trg_func_auto_score_posts() RETURNS trigger
            LANGUAGE plpgsql
            AS $$
        DECLARE
            title_text TEXT := COALESCE(NEW.title, '');
            body_text TEXT := COALESCE(NEW.body, '');
            full_text TEXT := title_text || ' ' || body_text;
            meta JSONB := COALESCE(NEW.metadata, '{}'::jsonb);
            pool_id INTEGER;
            quarantine_id BIGINT;
        BEGIN
            -- ===========================
            -- Step 0: Link Community
            -- ===========================
            -- Try to find community_id if not provided
            IF NEW.community_id IS NULL THEN
                SELECT id INTO pool_id FROM public.community_pool WHERE lower(name) = lower(NEW.subreddit);
                NEW.community_id := pool_id;
            END IF;

            IF NEW.community_id IS NULL THEN
                INSERT INTO public.posts_quarantine (
                    source, source_post_id, subreddit, title, body, author_name, reject_reason, original_payload
                )
                VALUES (
                    NEW.source, NEW.source_post_id, NEW.subreddit, NEW.title, NEW.body, NEW.author_name,
                    'community_unmapped', to_jsonb(NEW)
                )
                RETURNING id INTO quarantine_id;

                INSERT INTO public.data_audit_events (
                    event_type, target_type, target_id, reason, source_component, new_value
                )
                VALUES (
                    'quarantine', 'posts_quarantine', quarantine_id::text, 'community_unmapped',
                    'trg_func_auto_score_posts',
                    jsonb_build_object(
                        'subreddit', NEW.subreddit,
                        'source_post_id', NEW.source_post_id,
                        'source', NEW.source
                    )
                );
                RETURN NULL; -- 拦截入库
            END IF;

            -- ===========================
            -- Layer 1: 隔离 (Quarantine)
            -- ===========================
            
            -- 1.1 鬼魂/已删 (Ghost)
            IF body_text IN ('[deleted]', '[removed]') OR title_text = '' THEN
                INSERT INTO public.posts_quarantine (source, source_post_id, subreddit, title, body, author_name, reject_reason, original_payload)
                VALUES (NEW.source, NEW.source_post_id, NEW.subreddit, NEW.title, NEW.body, NEW.author_name, 'ghost_content', to_jsonb(NEW));
                RETURN NULL; -- 拦截入库
            END IF;

            -- 1.2 短内容 (Short) - < 10 chars
            IF LENGTH(full_text) < 10 THEN
                INSERT INTO public.posts_quarantine (source, source_post_id, subreddit, title, body, author_name, reject_reason, original_payload)
                VALUES (NEW.source, NEW.source_post_id, NEW.subreddit, NEW.title, NEW.body, NEW.author_name, 'short_content', to_jsonb(NEW));
                RETURN NULL; -- 拦截入库
            END IF;

            -- ===========================
            -- Layer 2/3: 打分 (Scoring)
            -- ===========================

            -- Set Lineage Info
            NEW.score_source := 'rule_v2';
            NEW.score_version := 2;

            -- 2.1 SPAM 检测 -> 0分
            IF (LENGTH(body_text) - LENGTH(REPLACE(body_text, 'http', ''))) / 4 > 2 
               OR body_text ~* 'bit\.ly|amzn\.to|t\.co|goo\.gl|tinyurl\.com'
               OR full_text ~* 'promo code|discount code|affiliate link|buy now|check out my|click here' THEN
                
                NEW.value_score := 0;
                NEW.spam_category := 'ad_auto_detected';
                NEW.business_pool := 'noise';
                RETURN NEW;
            END IF;

            -- 2.2 交易贴 (WTS) -> 6分
            IF title_text ~* '\[(WTS|WTT|WTB|S|B)\]' 
               OR title_text ~* '\b(selling|buying|trading)\b.*\b(price|usd|\$)\b' THEN
                NEW.value_score := 6;
                IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;
            
            -- 2.3 黄金决策 -> 7分
            ELSIF full_text ~* 'recommend|suggestion|which one|which should I| vs |versus|worth it|review|looking for|advice on' THEN
                NEW.value_score := 7;
                NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_decision"');
            
            -- 2.4 黄金痛点 -> 6分
            ELSIF full_text ~* 'how to|issue with|failed|broke|not working|help with|problem with|error|bug' THEN
                NEW.value_score := 6;
                NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_problem"');
            
            -- 2.5 价格敏感 -> 5分
            ELSIF title_text ~* '\b(price|budget|cost|worth)\b' AND title_text ~* '\$[0-9]+|[0-9]+(\s)?(usd|k)' THEN
                NEW.value_score := 5;
                IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;

            -- 2.6 默认 -> 3分
            ELSIF NEW.value_score IS NULL THEN
                NEW.value_score := 3;
                IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;
            END IF;

            -- ===========================
            -- Layer 4: 分池 (Pooling)
            -- ===========================
            
            IF NEW.value_score >= 8 THEN
                NEW.business_pool := 'core';
            ELSIF NEW.value_score <= 2 THEN
                NEW.business_pool := 'noise';
            ELSE
                NEW.business_pool := 'lab';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.safe_delete_community(community_name_param text)
        RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER
        AS $$
        DECLARE
            cache_deleted INTEGER := 0;
            pool_deleted INTEGER := 0;
            start_time TIMESTAMP WITH TIME ZONE := NOW();
        BEGIN
            DELETE FROM community_cache WHERE community_name = community_name_param;
            GET DIAGNOSTICS cache_deleted = ROW_COUNT;
            
            DELETE FROM community_pool WHERE name = community_name_param;
            GET DIAGNOSTICS pool_deleted = ROW_COUNT;

            INSERT INTO cleanup_logs (executed_at, total_records_cleaned, breakdown, duration_seconds, success)
            VALUES (
                start_time,
                cache_deleted + pool_deleted,
                jsonb_build_object(
                    'operation', 'safe_delete_community',
                    'community', community_name_param,
                    'cache_deleted', cache_deleted,
                    'pool_deleted', pool_deleted
                ),
                EXTRACT(EPOCH FROM (NOW() - start_time))::INTEGER,
                true
            );

            INSERT INTO data_audit_events (
                event_type, target_type, target_id, reason, source_component, new_value
            )
            VALUES (
                'delete', 'community_pool', community_name_param, 'safe_delete_community',
                'safe_delete_community',
                jsonb_build_object(
                    'cache_deleted', cache_deleted,
                    'pool_deleted', pool_deleted
                )
            );
            
            RETURN cache_deleted + pool_deleted;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS sync_pool_categories_from_map ON community_category_map")
    op.execute("DROP FUNCTION IF EXISTS public.trg_sync_pool_categories_from_map")
    op.execute("DROP TRIGGER IF EXISTS sync_category_map_from_pool ON community_pool")
    op.execute("DROP FUNCTION IF EXISTS public.trg_sync_category_map_from_pool")
    op.execute("DROP FUNCTION IF EXISTS public.sync_community_pool_categories_from_map")
    op.execute("DROP FUNCTION IF EXISTS public.sync_community_category_map_from_pool")
    op.execute("DROP FUNCTION IF EXISTS public.community_category_keys_from_jsonb")

    op.execute("DROP INDEX IF EXISTS ux_posts_raw_current")
    op.execute("DROP INDEX IF EXISTS ux_community_category_primary")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_posts_raw_community'
            ) THEN
                ALTER TABLE posts_raw DROP CONSTRAINT fk_posts_raw_community;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_posts_raw_community_id_not_null'
            ) THEN
                ALTER TABLE posts_raw DROP CONSTRAINT ck_posts_raw_community_id_not_null;
            END IF;
        END
        $$;
        """
    )

    op.drop_column("post_semantic_labels", "llm_version")
    op.drop_column("post_semantic_labels", "rule_version")
