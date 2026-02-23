--
-- PostgreSQL database dump
--

\restrict lBf4IsIow6Jaa7SL1faJE1W0J5SnpAz54dKPieylOfYeJp1ZLtrfyRK5hvvamt0

-- Dumped from database version 14.19 (Homebrew)
-- Dumped by pg_dump version 14.19 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: btree_gin; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gin WITH SCHEMA public;


--
-- Name: EXTENSION btree_gin; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION btree_gin IS 'support for indexing common datatypes in GIN';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: membership_level; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.membership_level AS ENUM (
    'free',
    'pro',
    'enterprise'
);


ALTER TYPE public.membership_level OWNER TO postgres;

--
-- Name: task_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.task_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'queued',
    'cancelled',
    'retrying',
    'dead_letter'
);


ALTER TYPE public.task_status OWNER TO postgres;

--
-- Name: adjust_comment_ttl_on_score(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.adjust_comment_ttl_on_score() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- 只有当 value_score 发生变化时才执行
        IF NEW.value_score IS DISTINCT FROM OLD.value_score THEN
            IF NEW.value_score >= 8 THEN
                NEW.expires_at := NULL; -- 晋升 Core，永生
                NEW.business_pool := 'core';
            ELSIF NEW.value_score <= 2 THEN
                NEW.expires_at := LEAST(NEW.created_utc + interval '30 days', NOW() + interval '7 days'); -- 降级 Noise，加速腐烂
                NEW.business_pool := 'noise';
            ELSE
                -- 保持 Lab 默认或原有逻辑 (不轻易改短，防止误伤)
                -- 但确保它在 Lab 池
                NEW.business_pool := 'lab';
                -- 如果之前是无限期 (NULL)，现在降级了，给它设个期限
                IF NEW.expires_at IS NULL THEN
                    NEW.expires_at := NEW.created_utc + interval '180 days';
                END IF;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$;


ALTER FUNCTION public.adjust_comment_ttl_on_score() OWNER TO postgres;

--
-- Name: archive_old_posts(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.archive_old_posts(days_to_keep integer DEFAULT 90, batch_size integer DEFAULT 1000) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            archived_count INTEGER;
            cutoff TIMESTAMP WITH TIME ZONE;
        BEGIN
            cutoff := NOW() - (days_to_keep || ' days')::INTERVAL;

            WITH moved_rows AS (
                SELECT id
                FROM posts_raw
                WHERE created_at < cutoff
                  AND is_current = FALSE
                ORDER BY created_at
                LIMIT batch_size
            )
            INSERT INTO posts_archive (source, source_post_id, version, archived_at, payload)
            SELECT
                pr.source,
                pr.source_post_id,
                pr.version,
                NOW(),
                to_jsonb(pr)
            FROM posts_raw pr
            JOIN moved_rows mr ON pr.id = mr.id;

            GET DIAGNOSTICS archived_count = ROW_COUNT;
            RETURN archived_count;
        END;
        $$;


ALTER FUNCTION public.archive_old_posts(days_to_keep integer, batch_size integer) OWNER TO postgres;

--
-- Name: calculate_comment_basic_score(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_comment_basic_score(body_text text) RETURNS smallint
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
    score smallint := 2; -- 基础分
BEGIN
    IF body_text IS NULL THEN
        RETURN 0;
    END IF;

    -- Rule 1: 话痨奖励 (>150 chars) -> +1
    IF length(body_text) > 150 THEN
        score := score + 1;
    END IF;

    -- Rule 2: 解决方案奖励 (Solution Keywords) -> +2
    IF body_text ~* '\b(fixed|solution|solved|bought|ordered|recommend|works well|use this|try this)\b' THEN
        score := score + 2;
    END IF;

    -- Rule 3: 提问奖励 (Question Keywords) -> +1
    IF body_text ~* '\?|\b(how|what|why|where|does anyone)\b' THEN
        score := score + 1;
    END IF;

    -- Cap at 5 (Max heuristic score)
    IF score > 5 THEN
        score := 5;
    END IF;

    RETURN score;
END;
$$;


ALTER FUNCTION public.calculate_comment_basic_score(body_text text) OWNER TO postgres;

--
-- Name: cleanup_completed_tasks(timestamp with time zone, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_completed_tasks(cutoff_date timestamp with time zone, batch_size integer DEFAULT 1000) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER := 0;
            current_batch INTEGER;
            loop_count INTEGER := 0;
        BEGIN
            -- 安全检查：确保cutoff_date不是未来时间
            IF cutoff_date > CURRENT_TIMESTAMP THEN
                RAISE EXCEPTION '清理截止日期不能是未来时间: %', cutoff_date;
            END IF;
            
            LOOP
                loop_count := loop_count + 1;
                
                -- 防止无限循环
                IF loop_count > 1000 THEN
                    RAISE EXCEPTION '清理循环次数超限，可能存在死循环';
                END IF;
                
                -- 分批删除避免长时间锁表
                WITH deleted AS (
                    DELETE FROM tasks 
                    WHERE status = 'completed' 
                      AND completed_at IS NOT NULL
                      AND completed_at < cutoff_date
                      AND id IN (
                          SELECT id FROM tasks 
                          WHERE status = 'completed' 
                            AND completed_at IS NOT NULL
                            AND completed_at < cutoff_date
                          ORDER BY completed_at ASC
                          LIMIT batch_size
                      )
                    RETURNING id
                )
                SELECT COUNT(*) INTO current_batch FROM deleted;
                
                deleted_count := deleted_count + current_batch;
                
                -- 如果这批没删除任何记录，说明清理完成
                IF current_batch = 0 THEN
                    EXIT;
                END IF;
                
                -- 短暂暂停，释放锁给其他事务
                PERFORM pg_sleep(0.1);
                
                -- 每删除10批提交一次，避免事务过长
                IF loop_count % 10 = 0 THEN
                    RAISE NOTICE '已清理 % 条完成任务记录', deleted_count;
                END IF;
            END LOOP;
            
            RAISE NOTICE '清理完成任务总计: % 条记录', deleted_count;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_completed_tasks(cutoff_date timestamp with time zone, batch_size integer) OWNER TO postgres;

--
-- Name: cleanup_expired_community_cache(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_expired_community_cache() RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            -- 清理超过TTL的缓存记录
            WITH deleted AS (
                DELETE FROM community_cache 
                WHERE last_crawled_at IS NOT NULL
                  AND ttl_seconds IS NOT NULL
                  AND ttl_seconds > 0
                  AND (last_crawled_at + INTERVAL '1 second' * ttl_seconds) < CURRENT_TIMESTAMP
                RETURNING community_name
            )
            SELECT COUNT(*) INTO deleted_count FROM deleted;
            
            RAISE NOTICE '清理过期缓存总计: % 条记录', deleted_count;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_expired_community_cache() OWNER TO postgres;

--
-- Name: cleanup_expired_hot_cache(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_expired_hot_cache() RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM posts_hot WHERE expires_at < NOW();
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_expired_hot_cache() OWNER TO postgres;

--
-- Name: FUNCTION cleanup_expired_hot_cache(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.cleanup_expired_hot_cache() IS '清理过期的热缓存';


--
-- Name: cleanup_failed_tasks(timestamp with time zone, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_failed_tasks(cutoff_date timestamp with time zone, batch_size integer DEFAULT 1000) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER := 0;
            current_batch INTEGER;
            loop_count INTEGER := 0;
        BEGIN
            -- 安全检查
            IF cutoff_date > CURRENT_TIMESTAMP THEN
                RAISE EXCEPTION '清理截止日期不能是未来时间: %', cutoff_date;
            END IF;
            
            LOOP
                loop_count := loop_count + 1;
                
                IF loop_count > 1000 THEN
                    RAISE EXCEPTION '清理循环次数超限，可能存在死循环';
                END IF;
                
                WITH deleted AS (
                    DELETE FROM tasks 
                    WHERE status = 'failed' 
                      AND updated_at IS NOT NULL
                      AND updated_at < cutoff_date
                      AND id IN (
                          SELECT id FROM tasks 
                          WHERE status = 'failed' 
                            AND updated_at IS NOT NULL
                            AND updated_at < cutoff_date
                          ORDER BY updated_at ASC
                          LIMIT batch_size
                      )
                    RETURNING id
                )
                SELECT COUNT(*) INTO current_batch FROM deleted;
                
                deleted_count := deleted_count + current_batch;
                
                IF current_batch = 0 THEN
                    EXIT;
                END IF;
                
                PERFORM pg_sleep(0.1);
                
                IF loop_count % 10 = 0 THEN
                    RAISE NOTICE '已清理 % 条失败任务记录', deleted_count;
                END IF;
            END LOOP;
            
            RAISE NOTICE '清理失败任务总计: % 条记录', deleted_count;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_failed_tasks(cutoff_date timestamp with time zone, batch_size integer) OWNER TO postgres;

--
-- Name: cleanup_inactive_users(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_inactive_users(cutoff_date timestamp with time zone) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            updated_count INTEGER;
        BEGIN
            -- 安全检查
            IF cutoff_date > CURRENT_TIMESTAMP - INTERVAL '30 days' THEN
                RAISE EXCEPTION '非活跃用户清理时间不能少于30天: %', cutoff_date;
            END IF;
            
            -- 标记为软删除，不物理删除
            WITH updated AS (
                UPDATE users 
                SET 
                    is_active = false,
                    updated_at = CURRENT_TIMESTAMP
                WHERE is_active = true
                  AND (updated_at < cutoff_date)
                  AND created_at < cutoff_date - INTERVAL '7 days'  -- 新用户保护期
                  AND id NOT IN (
                      -- 保护有活跃任务的用户
                      SELECT DISTINCT user_id FROM tasks 
                      WHERE user_id IS NOT NULL
                        AND created_at > cutoff_date
                  )
                RETURNING id
            )
            SELECT COUNT(*) INTO updated_count FROM updated;
            
            RAISE NOTICE '软删除非活跃用户总计: % 个用户', updated_count;
            RETURN updated_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_inactive_users(cutoff_date timestamp with time zone) OWNER TO postgres;

--
-- Name: cleanup_low_confidence_analyses(numeric, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_low_confidence_analyses(confidence_threshold numeric DEFAULT 0.3, days_old integer DEFAULT 90) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM analyses 
            WHERE confidence_score < confidence_threshold
              AND created_at < CURRENT_TIMESTAMP - (days_old || ' days')::INTERVAL;
            
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_low_confidence_analyses(confidence_threshold numeric, days_old integer) OWNER TO postgres;

--
-- Name: cleanup_old_posts(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_old_posts(days_to_keep integer DEFAULT 90) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER;
            cutoff_date TIMESTAMP WITH TIME ZONE;
        BEGIN
            PERFORM archive_old_posts(days_to_keep, 5000);

            cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

            DELETE FROM posts_raw
            WHERE created_at < cutoff_date
              AND is_current = FALSE;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_old_posts(days_to_keep integer) OWNER TO postgres;

--
-- Name: cleanup_orphan_analyses(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_orphan_analyses(cutoff_time timestamp with time zone) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            -- 安全检查
            IF cutoff_time > CURRENT_TIMESTAMP THEN
                RAISE EXCEPTION '清理截止时间不能是未来时间: %', cutoff_time;
            END IF;
            
            -- 删除没有对应task的analysis记录
            -- 使用LEFT JOIN确保安全性
            WITH deleted AS (
                DELETE FROM analyses 
                WHERE id IN (
                    SELECT a.id 
                    FROM analyses a
                    LEFT JOIN tasks t ON a.task_id = t.id
                    WHERE t.id IS NULL
                      AND a.created_at < cutoff_time
                )
                RETURNING id
            )
            SELECT COUNT(*) INTO deleted_count FROM deleted;
            
            RAISE NOTICE '清理孤儿分析记录总计: % 条记录', deleted_count;
            RETURN deleted_count;
        END;
        $$;


ALTER FUNCTION public.cleanup_orphan_analyses(cutoff_time timestamp with time zone) OWNER TO postgres;

--
-- Name: execute_data_cleanup(integer, integer, numeric, integer, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.execute_data_cleanup(completed_task_days integer DEFAULT 30, failed_task_days integer DEFAULT 7, orphan_analysis_hours numeric DEFAULT 1, inactive_user_days integer DEFAULT 365, dry_run boolean DEFAULT false) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
        DECLARE
            results JSONB;
            completed_count INTEGER := 0;
            failed_count INTEGER := 0;
            orphan_count INTEGER := 0;
            cache_count INTEGER := 0;
            user_count INTEGER := 0;
            start_time TIMESTAMP WITH TIME ZONE;
            end_time TIMESTAMP WITH TIME ZONE;
            log_id UUID;
        BEGIN
            start_time := CURRENT_TIMESTAMP;
            
            -- 如果是试运行，只统计不删除
            IF dry_run THEN
                -- 统计将要清理的记录数
                SELECT COUNT(*) INTO completed_count
                FROM tasks 
                WHERE status = 'completed' 
                  AND completed_at IS NOT NULL
                  AND completed_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * completed_task_days;
                
                SELECT COUNT(*) INTO failed_count
                FROM tasks 
                WHERE status = 'failed' 
                  AND updated_at IS NOT NULL
                  AND updated_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * failed_task_days;
                
                SELECT COUNT(*) INTO orphan_count
                FROM analyses a
                LEFT JOIN tasks t ON a.task_id = t.id
                WHERE t.id IS NULL
                  AND a.created_at < CURRENT_TIMESTAMP - INTERVAL '1 hour' * orphan_analysis_hours;
                
                SELECT COUNT(*) INTO cache_count
                FROM community_cache 
                WHERE last_crawled_at IS NOT NULL
                  AND ttl_seconds IS NOT NULL
                  AND ttl_seconds > 0
                  AND (last_crawled_at + INTERVAL '1 second' * ttl_seconds) < CURRENT_TIMESTAMP;
                
                SELECT COUNT(*) INTO user_count
                FROM users 
                WHERE is_active = true
                  AND (updated_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * inactive_user_days);
            ELSE
                -- 执行实际清理
                SELECT cleanup_completed_tasks(
                    CURRENT_TIMESTAMP - INTERVAL '1 day' * completed_task_days
                ) INTO completed_count;
                
                SELECT cleanup_failed_tasks(
                    CURRENT_TIMESTAMP - INTERVAL '1 day' * failed_task_days
                ) INTO failed_count;
                
                SELECT cleanup_orphan_analyses(
                    CURRENT_TIMESTAMP - INTERVAL '1 hour' * orphan_analysis_hours
                ) INTO orphan_count;
                
                SELECT cleanup_expired_community_cache() INTO cache_count;
                
                SELECT cleanup_inactive_users(
                    CURRENT_TIMESTAMP - INTERVAL '1 day' * inactive_user_days
                ) INTO user_count;
            END IF;
            
            end_time := CURRENT_TIMESTAMP;
            
            -- 构建结果JSON
            results := jsonb_build_object(
                'completed_tasks', completed_count,
                'failed_tasks', failed_count,
                'orphan_analyses', orphan_count,
                'expired_cache', cache_count,
                'inactive_users', user_count,
                'total_cleaned', completed_count + failed_count + orphan_count + cache_count + user_count,
                'duration_seconds', EXTRACT(EPOCH FROM (end_time - start_time))::INTEGER,
                'dry_run', dry_run,
                'executed_at', start_time
            );
            
            -- 记录清理日志（只有实际执行才记录）
            IF NOT dry_run THEN
                INSERT INTO cleanup_logs 
                (executed_at, total_records_cleaned, breakdown, duration_seconds, success)
                VALUES (
                    start_time,
                    completed_count + failed_count + orphan_count + cache_count + user_count,
                    results,
                    EXTRACT(EPOCH FROM (end_time - start_time))::INTEGER,
                    true
                );
            END IF;
            
            RETURN results;
        END;
        $$;


ALTER FUNCTION public.execute_data_cleanup(completed_task_days integer, failed_task_days integer, orphan_analysis_hours numeric, inactive_user_days integer, dry_run boolean) OWNER TO postgres;

--
-- Name: fill_normalized_fields(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fill_normalized_fields() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.body_norm := regexp_replace(
                regexp_replace(lower(trim(COALESCE(NEW.body, ''))), '[^a-z0-9\s]', '', 'g'),
                '\s+',
                ' ',
                'g'
            );

            NEW.text_norm_hash := text_norm_hash(NEW.title || ' ' || COALESCE(NEW.body, ''));
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.fill_normalized_fields() OWNER TO postgres;

--
-- Name: FUNCTION fill_normalized_fields(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.fill_normalized_fields() IS '自动填充归一化字段';


--
-- Name: get_storage_stats(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_storage_stats() RETURNS TABLE(metric character varying, value bigint)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RETURN QUERY
            SELECT 'posts_raw_total'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_raw
            UNION ALL
            SELECT 'posts_raw_current'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_raw WHERE is_current = TRUE
            UNION ALL
            SELECT 'posts_hot_total'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_hot
            UNION ALL
            SELECT 'posts_hot_expired'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_hot WHERE expires_at < NOW()
            UNION ALL
            SELECT 'unique_subreddits'::VARCHAR(50), COUNT(DISTINCT subreddit)::BIGINT FROM posts_raw
            UNION ALL
            SELECT 'total_versions'::VARCHAR(50), SUM(version)::BIGINT FROM posts_raw WHERE is_current = TRUE;
        END;
        $$;


ALTER FUNCTION public.get_storage_stats() OWNER TO postgres;

--
-- Name: FUNCTION get_storage_stats(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.get_storage_stats() IS '获取存储统计信息';


--
-- Name: rebuild_analyses_gin_indexes(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rebuild_analyses_gin_indexes() RETURNS void
    LANGUAGE plpgsql
    AS $$
        BEGIN
            REINDEX INDEX CONCURRENTLY ix_analyses_insights_gin;
            REINDEX INDEX CONCURRENTLY ix_analyses_sources_gin;
        END;
        $$;


ALTER FUNCTION public.rebuild_analyses_gin_indexes() OWNER TO postgres;

--
-- Name: refresh_mining_views(); Type: PROCEDURE; Schema: public; Owner: hujia
--

CREATE PROCEDURE public.refresh_mining_views()
    LANGUAGE plpgsql
    AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_labels;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_entities;
END;
$$;


ALTER PROCEDURE public.refresh_mining_views() OWNER TO hujia;

--
-- Name: refresh_posts_latest(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.refresh_posts_latest() RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            refresh_count INTEGER;
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY posts_latest;
            GET DIAGNOSTICS refresh_count = ROW_COUNT;
            RETURN refresh_count;
        END;
        $$;


ALTER FUNCTION public.refresh_posts_latest() OWNER TO postgres;

--
-- Name: FUNCTION refresh_posts_latest(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.refresh_posts_latest() IS '刷新 posts_latest 物化视图';


--
-- Name: safe_delete_community(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.safe_delete_community(community_name_param text) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    cache_deleted INTEGER := 0;
    pool_deleted INTEGER := 0;
BEGIN
    DELETE FROM community_cache WHERE community_name = community_name_param;
    GET DIAGNOSTICS cache_deleted = ROW_COUNT;
    
    DELETE FROM community_pool WHERE name = community_name_param;
    GET DIAGNOSTICS pool_deleted = ROW_COUNT;
    
    RETURN cache_deleted + pool_deleted;
END;
$$;


ALTER FUNCTION public.safe_delete_community(community_name_param text) OWNER TO postgres;

--
-- Name: set_comment_expires_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.set_comment_expires_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- 只有当没有显式指定 expires_at 时才自动计算
            IF NEW.expires_at IS NULL THEN
                NEW.expires_at := CASE
                    -- 如果一开始就有分 (极少情况)，直接应用分级策略
                    WHEN NEW.value_score >= 8 THEN NULL  -- Core: 永不过期
                    WHEN NEW.value_score <= 2 AND NEW.value_score IS NOT NULL THEN NEW.created_utc + interval '30 days' -- Noise: 30天
                    -- 默认逻辑 (基于 Reddit Score)
                    WHEN NEW.score > 100 OR NEW.awards_count > 5 THEN NEW.created_utc + interval '365 days'
                    WHEN NEW.score > 10 THEN NEW.created_utc + interval '180 days'
                    ELSE NEW.created_utc + interval '90 days'
                END;
            END IF;
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.set_comment_expires_at() OWNER TO postgres;

--
-- Name: text_norm_hash(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.text_norm_hash(content text) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $$
        DECLARE
            normalized TEXT;
        BEGIN
            normalized := regexp_replace(
                lower(trim(COALESCE(content, ''))),
                '[^a-z0-9\s]',
                '',
                'g'
            );
            normalized := regexp_replace(normalized, '\s+', ' ', 'g');

            RETURN encode(digest(normalized, 'sha256'), 'hex');
        END;
        $$;


ALTER FUNCTION public.text_norm_hash(content text) OWNER TO postgres;

--
-- Name: trg_func_auto_clean_comments(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.trg_func_auto_clean_comments() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
        calc_score smallint;
    BEGIN
        -- Layer 1: 扫地 (Hygiene)
        -- 1.1 显性垃圾
        IF NEW.body ~* '^\[(deleted|removed)\]$' OR NEW.body IS NULL THEN
            NEW.business_pool := 'noise';
            NEW.value_score := 0;
            NEW.is_deleted := TRUE;
            RETURN NEW;
        END IF;

        -- 1.2 短文本
        IF length(NEW.body) < 10 THEN
            NEW.business_pool := 'noise';
            NEW.value_score := 0;
            RETURN NEW;
        END IF;

        -- 1.3 垃圾关键词 (Spam)
        IF NEW.body ~* '\b(promo code|coupon|discount|affiliate|click here|whatsapp)\b' THEN
            NEW.business_pool := 'noise';
            NEW.value_score := 0;
            RETURN NEW;
        END IF;

        -- Layer 2: 算分 (Heuristic Scoring)
        calc_score := public.calculate_comment_basic_score(NEW.body);
        NEW.value_score := calc_score;

        -- Layer 3: 分池 (Pooling)
        IF calc_score >= 4 THEN
            -- 高分 -> Lab 候选 (High Potential)
            NEW.business_pool := 'lab';
        ELSIF calc_score >= 1 THEN
            -- 普通 -> Lab (Normal)
            NEW.business_pool := 'lab';
        ELSE
            -- 低分 -> Noise
            NEW.business_pool := 'noise';
        END IF;

        RETURN NEW;
    END;
    $_$;


ALTER FUNCTION public.trg_func_auto_clean_comments() OWNER TO postgres;

--
-- Name: trg_func_auto_score_posts(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.trg_func_auto_score_posts() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    title_text TEXT := COALESCE(NEW.title, '');
    body_text TEXT := COALESCE(NEW.body, '');
    full_text TEXT := title_text || ' ' || body_text;
    meta JSONB := COALESCE(NEW.metadata, '{}'::jsonb);
    pool_id INTEGER;
BEGIN
    -- ===========================
    -- Step 0: Link Community
    -- ===========================
    -- Try to find community_id if not provided
    IF NEW.community_id IS NULL THEN
        SELECT id INTO pool_id FROM public.community_pool WHERE lower(name) = lower(NEW.subreddit);
        NEW.community_id := pool_id;
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
$_$;


ALTER FUNCTION public.trg_func_auto_score_posts() OWNER TO postgres;

--
-- Name: trg_posts_raw_enforce_scd2(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.trg_posts_raw_enforce_scd2() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- 场景 1: 新插入 (INSERT)
    -- 保留调用方提供的版本号；若为空则默认 1
    IF (TG_OP = 'INSERT') THEN
        NEW.version := COALESCE(NEW.version, 1);
        NEW.is_current := COALESCE(NEW.is_current, true);
        NEW.valid_from := COALESCE(NEW.valid_from, NOW());
        NEW.valid_to := COALESCE(NEW.valid_to, '9999-12-31 00:00:00'::timestamp);
        RETURN NEW;
    END IF;

    -- 场景 2: 更新 (UPDATE)
    IF (TG_OP = 'UPDATE') THEN
        -- 实质性变更：关旧开新
        IF (NEW.title IS DISTINCT FROM OLD.title OR NEW.body IS DISTINCT FROM OLD.body) THEN
            UPDATE public.posts_raw
            SET is_current = false,
                valid_to = NOW()
            WHERE id = OLD.id;

            INSERT INTO public.posts_raw (
                source, source_post_id, version,
                created_at, fetched_at, valid_from, valid_to, is_current,
                author_id, author_name, title, body, body_norm, text_norm_hash,
                url, subreddit, score, num_comments, is_deleted, edit_count, lang, metadata
            ) VALUES (
                NEW.source, NEW.source_post_id, COALESCE(NEW.version, OLD.version + 1),
                OLD.created_at, NOW(), NOW(), '9999-12-31 00:00:00', true,
                NEW.author_id, NEW.author_name, NEW.title, NEW.body, NEW.body_norm, NEW.text_norm_hash,
                NEW.url, NEW.subreddit, NEW.score, NEW.num_comments, NEW.is_deleted, NEW.edit_count, NEW.lang, NEW.metadata
            );
            RETURN NULL; -- 取消原始 UPDATE
        ELSE
            -- 非实质变更：原地更新
            NEW.version := OLD.version;
            NEW.valid_from := OLD.valid_from;
            NEW.valid_to := OLD.valid_to;
            NEW.is_current := OLD.is_current;
            RETURN NEW;
        END IF;
    END IF;

    RETURN NULL;
END;
$$;


ALTER FUNCTION public.trg_posts_raw_enforce_scd2() OWNER TO postgres;

--
-- Name: update_cache_hit_stats(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_cache_hit_stats() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- 只在hit_count增加时更新last_hit_at
        IF NEW.hit_count > OLD.hit_count THEN
            NEW.last_hit_at = CURRENT_TIMESTAMP;
        END IF;
        
        RETURN NEW;
    END;
    $$;


ALTER FUNCTION public.update_cache_hit_stats() OWNER TO postgres;

--
-- Name: update_task_completion_status(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_task_completion_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- 更新关联任务状态为已完成
            UPDATE tasks 
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.task_id 
              AND status = 'processing';
            
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.update_task_completion_status() OWNER TO postgres;

--
-- Name: update_tasks_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_tasks_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.update_tasks_updated_at() OWNER TO postgres;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

--
-- Name: validate_insights_schema(jsonb); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.validate_insights_schema(data jsonb) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- 必须是对象类型
        IF jsonb_typeof(data) != 'object' THEN
            RETURN false;
        END IF;
        
        -- 必须包含三个核心字段
        IF NOT (data ? 'pain_points' AND data ? 'competitors' AND data ? 'opportunities') THEN
            RETURN false;
        END IF;
        
        -- 每个字段必须是数组
        IF jsonb_typeof(data->'pain_points') != 'array' OR
           jsonb_typeof(data->'competitors') != 'array' OR 
           jsonb_typeof(data->'opportunities') != 'array' THEN
            RETURN false;
        END IF;
        
        -- 验证pain_points结构
        IF EXISTS (
            SELECT 1 FROM jsonb_array_elements(data->'pain_points') AS item
            WHERE NOT (item ? 'description' AND item ? 'frequency' AND item ? 'sentiment_score')
        ) THEN
            RETURN false;
        END IF;
        
        RETURN true;
    END;
    $$;


ALTER FUNCTION public.validate_insights_schema(data jsonb) OWNER TO postgres;

--
-- Name: validate_sources_schema(jsonb); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.validate_sources_schema(data jsonb) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE
    AS $_$
        DECLARE
            community text;
        BEGIN
            IF jsonb_typeof(data) != 'object' THEN
                RETURN false;
            END IF;

            IF NOT (
                data ? 'communities'
                AND data ? 'posts_analyzed'
                AND data ? 'cache_hit_rate'
                AND data ? 'analysis_duration_seconds'
                AND data ? 'reddit_api_calls'
            ) THEN
                RETURN false;
            END IF;

            IF jsonb_typeof(data->'communities') != 'array' THEN
                RETURN false;
            END IF;

            FOR community IN SELECT jsonb_array_elements_text(data->'communities')
            LOOP
                IF community IS NULL OR NOT community ~ '^r/[a-zA-Z0-9_]+$' THEN
                    RETURN false;
                END IF;
            END LOOP;

            IF jsonb_typeof(data->'posts_analyzed') != 'number'
               OR jsonb_typeof(data->'cache_hit_rate') != 'number'
               OR jsonb_typeof(data->'analysis_duration_seconds') != 'number'
               OR jsonb_typeof(data->'reddit_api_calls') != 'number' THEN
                RETURN false;
            END IF;

            IF (data->>'posts_analyzed')::numeric < 0
               OR (data->>'cache_hit_rate')::numeric < 0
               OR (data->>'cache_hit_rate')::numeric > 1
               OR (data->>'analysis_duration_seconds')::numeric < 0
               OR (data->>'reddit_api_calls')::numeric < 0 THEN
                RETURN false;
            END IF;

            RETURN true;

        EXCEPTION
            WHEN OTHERS THEN
                RETURN false;
        END;
        $_$;


ALTER FUNCTION public.validate_sources_schema(data jsonb) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: analyses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analyses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid NOT NULL,
    insights jsonb NOT NULL,
    sources jsonb NOT NULL,
    confidence_score numeric(3,2),
    analysis_version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    action_items jsonb,
    CONSTRAINT ck_analyses_confidence_range CHECK (((confidence_score >= 0.00) AND (confidence_score <= 1.00))),
    CONSTRAINT ck_analyses_version_positive CHECK ((analysis_version > 0))
);
ALTER TABLE ONLY public.analyses ALTER COLUMN insights SET STATISTICS 1000;
ALTER TABLE ONLY public.analyses ALTER COLUMN sources SET STATISTICS 1000;


ALTER TABLE public.analyses OWNER TO postgres;

--
-- Name: analytics_community_history; Type: TABLE; Schema: public; Owner: hujia
--

CREATE TABLE public.analytics_community_history (
    report_date date DEFAULT CURRENT_DATE NOT NULL,
    subreddit character varying(100) NOT NULL,
    active_users_24h integer,
    posts_24h integer,
    pain_points_count integer,
    commercial_density numeric(5,2),
    c_score numeric(5,2)
);


ALTER TABLE public.analytics_community_history OWNER TO hujia;

--
-- Name: authors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authors (
    author_id character varying(100) NOT NULL,
    author_name character varying(100),
    created_utc timestamp with time zone,
    is_bot boolean DEFAULT false NOT NULL,
    first_seen_at_global timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.authors OWNER TO postgres;

--
-- Name: beta_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.beta_feedback (
    id uuid NOT NULL,
    task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    satisfaction integer NOT NULL,
    missing_communities text[] DEFAULT '{}'::text[] NOT NULL,
    comments text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT beta_feedback_satisfaction_check CHECK (((satisfaction >= 1) AND (satisfaction <= 5)))
);


ALTER TABLE public.beta_feedback OWNER TO postgres;

--
-- Name: business_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.business_categories (
    key character varying(50) NOT NULL,
    display_name character varying(100),
    description text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.business_categories OWNER TO postgres;

--
-- Name: TABLE business_categories; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.business_categories IS '权威业务分类字典表，强制唯一定义';


--
-- Name: cleanup_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cleanup_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    executed_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    total_records_cleaned integer NOT NULL,
    breakdown jsonb NOT NULL,
    duration_seconds integer,
    success boolean DEFAULT true NOT NULL,
    error_message text
);


ALTER TABLE public.cleanup_logs OWNER TO postgres;

--
-- Name: cleanup_stats; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.cleanup_stats AS
 SELECT date_trunc('day'::text, cleanup_logs.executed_at) AS cleanup_date,
    count(*) AS cleanup_runs,
    avg(cleanup_logs.total_records_cleaned) AS avg_records_cleaned,
    max(cleanup_logs.total_records_cleaned) AS max_records_cleaned,
    avg(cleanup_logs.duration_seconds) AS avg_duration_seconds,
    (((sum(
        CASE
            WHEN cleanup_logs.success THEN 1
            ELSE 0
        END))::double precision / (count(*))::double precision) * (100)::double precision) AS success_rate_percent
   FROM public.cleanup_logs
  WHERE (cleanup_logs.executed_at >= (CURRENT_TIMESTAMP - '30 days'::interval))
  GROUP BY (date_trunc('day'::text, cleanup_logs.executed_at))
  ORDER BY (date_trunc('day'::text, cleanup_logs.executed_at)) DESC;


ALTER TABLE public.cleanup_stats OWNER TO postgres;

--
-- Name: comment_scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comment_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id bigint NOT NULL,
    llm_version character varying(50) NOT NULL,
    rule_version character varying(50) NOT NULL,
    scored_at timestamp with time zone DEFAULT now(),
    is_latest boolean DEFAULT true,
    value_score numeric(4,2),
    opportunity_score numeric(4,2),
    business_pool character varying(20),
    sentiment numeric(4,3),
    purchase_intent_score numeric(4,2),
    tags_analysis jsonb DEFAULT '{}'::jsonb,
    entities_extracted jsonb DEFAULT '[]'::jsonb,
    calculation_log jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT comment_scores_business_pool_check CHECK (((business_pool)::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying])::text[])))
);


ALTER TABLE public.comment_scores OWNER TO postgres;

--
-- Name: comment_scores_latest_v; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.comment_scores_latest_v AS
 WITH has_primary AS (
         SELECT (EXISTS ( SELECT 1
                   FROM public.comment_scores comment_scores_1
                  WHERE ((comment_scores_1.is_latest = true) AND ((comment_scores_1.rule_version)::text <> 'rulebook_v1'::text)))) AS has_primary
        )
 SELECT comment_scores.comment_id,
    comment_scores.rule_version,
    comment_scores.llm_version,
    comment_scores.value_score,
    comment_scores.opportunity_score,
    comment_scores.business_pool,
    comment_scores.sentiment,
    comment_scores.purchase_intent_score,
    comment_scores.tags_analysis,
    comment_scores.entities_extracted,
    comment_scores.calculation_log,
    comment_scores.scored_at
   FROM public.comment_scores,
    has_primary
  WHERE ((comment_scores.is_latest = true) AND (((has_primary.has_primary = false) AND ((comment_scores.rule_version)::text = 'rulebook_v1'::text)) OR ((has_primary.has_primary = true) AND ((comment_scores.rule_version)::text <> 'rulebook_v1'::text))));


ALTER TABLE public.comment_scores_latest_v OWNER TO postgres;

--
-- Name: comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comments (
    id bigint NOT NULL,
    reddit_comment_id character varying(32) NOT NULL,
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    subreddit character varying(100) NOT NULL,
    parent_id character varying(32),
    depth integer DEFAULT 0 NOT NULL,
    body text NOT NULL,
    author_id character varying(100),
    author_name character varying(100),
    author_created_utc timestamp with time zone,
    created_utc timestamp with time zone NOT NULL,
    score integer DEFAULT 0 NOT NULL,
    is_submitter boolean DEFAULT false NOT NULL,
    distinguished character varying(32),
    edited boolean DEFAULT false NOT NULL,
    permalink text,
    removed_by_category character varying(64),
    awards_count integer DEFAULT 0 NOT NULL,
    captured_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone,
    post_id bigint NOT NULL,
    value_score smallint,
    business_pool character varying(10) DEFAULT 'lab'::character varying,
    is_deleted boolean DEFAULT false,
    lang character varying(10),
    source_track character varying(32) DEFAULT 'incremental'::character varying,
    first_seen_at timestamp with time zone DEFAULT now(),
    fetched_at timestamp with time zone DEFAULT now(),
    crawl_run_id uuid,
    community_run_id uuid,
    CONSTRAINT ck_comments_depth_nonneg CHECK ((depth >= 0)),
    CONSTRAINT ck_comments_subreddit_format CHECK (((subreddit)::text ~ '^r/[a-z0-9_]+$'::text)),
    CONSTRAINT comments_business_pool_check CHECK (((business_pool)::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying])::text[]))),
    CONSTRAINT comments_value_score_check CHECK (((value_score >= 0) AND (value_score <= 10)))
);


ALTER TABLE public.comments OWNER TO postgres;

--
-- Name: comments_core_lab_v; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.comments_core_lab_v AS
 SELECT c.id,
    c.reddit_comment_id,
    c.source,
    c.source_post_id,
    c.subreddit,
    c.parent_id,
    c.depth,
    c.body,
    c.author_id,
    c.author_name,
    c.author_created_utc,
    c.created_utc,
    c.score,
    c.is_submitter,
    c.distinguished,
    c.edited,
    c.permalink,
    c.removed_by_category,
    c.awards_count,
    c.captured_at,
    c.expires_at,
    c.post_id,
    c.value_score,
    c.business_pool,
    c.is_deleted,
    c.lang,
    c.source_track,
    c.first_seen_at,
    c.fetched_at,
    c.crawl_run_id
   FROM (public.comments c
     LEFT JOIN public.comment_scores_latest_v s ON ((s.comment_id = c.id)))
  WHERE ((COALESCE(s.business_pool, c.business_pool, 'lab'::character varying))::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying])::text[]));


ALTER TABLE public.comments_core_lab_v OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comments_id_seq OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: community_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_audit (
    id integer NOT NULL,
    community_id bigint NOT NULL,
    action text NOT NULL,
    metrics jsonb,
    reason text,
    actor text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT community_audit_action_check CHECK ((action = ANY (ARRAY['promote'::text, 'demote'::text, 'blacklist'::text, 'restore'::text])))
);


ALTER TABLE public.community_audit OWNER TO postgres;

--
-- Name: community_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.community_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_audit_id_seq OWNER TO postgres;

--
-- Name: community_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.community_audit_id_seq OWNED BY public.community_audit.id;


--
-- Name: community_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_cache (
    community_name character varying(100) NOT NULL,
    last_crawled_at timestamp with time zone,
    ttl_seconds integer DEFAULT 3600 NOT NULL,
    posts_cached integer DEFAULT 0 NOT NULL,
    hit_count integer DEFAULT 0 NOT NULL,
    last_hit_at timestamp with time zone,
    crawl_priority integer DEFAULT 50 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    crawl_frequency_hours integer DEFAULT 2 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    empty_hit integer DEFAULT 0 NOT NULL,
    success_hit integer DEFAULT 0 NOT NULL,
    failure_hit integer DEFAULT 0 NOT NULL,
    avg_valid_posts integer DEFAULT 0 NOT NULL,
    quality_tier character varying(20) NOT NULL,
    last_seen_post_id character varying(100),
    last_seen_created_at timestamp with time zone,
    total_posts_fetched integer DEFAULT 0 NOT NULL,
    dedup_rate numeric(5,2),
    member_count integer,
    crawl_quality_score numeric(3,2) DEFAULT 0.0 NOT NULL,
    community_key character varying(100) GENERATED ALWAYS AS (lower(regexp_replace((community_name)::text, '^r/'::text, ''::text))) STORED NOT NULL,
    backfill_floor timestamp with time zone,
    last_attempt_at timestamp with time zone,
    CONSTRAINT ck_cache_avg_valid_nonneg CHECK ((avg_valid_posts >= 0)),
    CONSTRAINT ck_cache_empty_hit_nonneg CHECK ((empty_hit >= 0)),
    CONSTRAINT ck_cache_failure_hit_nonneg CHECK ((failure_hit >= 0)),
    CONSTRAINT ck_cache_quality_range CHECK (((crawl_quality_score >= (0)::numeric) AND (crawl_quality_score <= (10)::numeric))),
    CONSTRAINT ck_cache_success_hit_nonneg CHECK ((success_hit >= 0)),
    CONSTRAINT ck_cache_total_nonneg CHECK ((total_posts_fetched >= 0)),
    CONSTRAINT ck_community_cache_ck_community_cache_name_format CHECK (((community_name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_community_cache_hit_count_non_negative CHECK ((hit_count >= 0)),
    CONSTRAINT ck_community_cache_member_count_nonneg CHECK (((member_count IS NULL) OR (member_count >= 0))),
    CONSTRAINT ck_community_cache_name_format CHECK (((community_name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_community_cache_posts_non_negative CHECK ((posts_cached >= 0)),
    CONSTRAINT ck_community_cache_priority_range CHECK (((crawl_priority >= 1) AND (crawl_priority <= 100))),
    CONSTRAINT ck_community_cache_ttl_positive CHECK ((ttl_seconds > 0))
);


ALTER TABLE public.community_cache OWNER TO postgres;

--
-- Name: TABLE community_cache; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.community_cache IS '社区缓存元数据表 - Reddit社区数据的缓存状态管理，支持LRU + TTL + Priority三重缓存策略';


--
-- Name: COLUMN community_cache.community_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.community_name IS 'Reddit社区名称，如r/startups';


--
-- Name: COLUMN community_cache.last_crawled_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_crawled_at IS '最后抓取时间，NULL表示从未抓取';


--
-- Name: COLUMN community_cache.ttl_seconds; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.ttl_seconds IS '缓存生存时间（秒）';


--
-- Name: COLUMN community_cache.posts_cached; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.posts_cached IS '当前缓存的帖子数量';


--
-- Name: COLUMN community_cache.hit_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.hit_count IS '缓存命中次数';


--
-- Name: COLUMN community_cache.last_hit_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_hit_at IS '最后访问时间';


--
-- Name: COLUMN community_cache.crawl_priority; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.crawl_priority IS '爬虫优先级(1-100)，1为最高';


--
-- Name: COLUMN community_cache.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.created_at IS '缓存条目创建时间';


--
-- Name: COLUMN community_cache.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.updated_at IS '缓存元数据最后更新时间';


--
-- Name: COLUMN community_cache.last_seen_post_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_seen_post_id IS '水位线：最后抓取的帖子ID';


--
-- Name: COLUMN community_cache.last_seen_created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_seen_created_at IS '水位线：最后抓取的帖子创建时间';


--
-- Name: COLUMN community_cache.total_posts_fetched; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.total_posts_fetched IS '累计抓取的帖子数';


--
-- Name: COLUMN community_cache.dedup_rate; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.dedup_rate IS '去重率（%）';


--
-- Name: COLUMN community_cache.member_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.member_count IS 'Number of members in the community (from Reddit API)';


--
-- Name: community_category_map; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_category_map (
    community_id integer NOT NULL,
    category_key character varying(50) NOT NULL,
    is_primary boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.community_category_map OWNER TO postgres;

--
-- Name: TABLE community_category_map; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.community_category_map IS '社区与业务分类的关联表 (打标)';


--
-- Name: community_import_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_import_history (
    id integer NOT NULL,
    filename character varying(255) NOT NULL,
    uploaded_by character varying(255) NOT NULL,
    uploaded_by_user_id uuid,
    dry_run boolean DEFAULT false NOT NULL,
    status character varying(32) NOT NULL,
    total_rows integer DEFAULT 0 NOT NULL,
    valid_rows integer DEFAULT 0 NOT NULL,
    invalid_rows integer DEFAULT 0 NOT NULL,
    duplicate_rows integer DEFAULT 0 NOT NULL,
    imported_rows integer DEFAULT 0 NOT NULL,
    error_details jsonb,
    summary_preview jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by uuid,
    updated_by uuid
);


ALTER TABLE public.community_import_history OWNER TO postgres;

--
-- Name: community_import_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.community_import_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_import_history_id_seq OWNER TO postgres;

--
-- Name: community_import_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.community_import_history_id_seq OWNED BY public.community_import_history.id;


--
-- Name: community_pool; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_pool (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    tier character varying(20) NOT NULL,
    categories jsonb NOT NULL,
    description_keywords jsonb NOT NULL,
    daily_posts integer DEFAULT 0 NOT NULL,
    avg_comment_length integer DEFAULT 0 NOT NULL,
    user_feedback_count integer DEFAULT 0 NOT NULL,
    discovered_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    priority character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    is_blacklisted boolean DEFAULT false NOT NULL,
    blacklist_reason character varying(255),
    downrank_factor numeric(3,2),
    created_by uuid,
    updated_by uuid,
    deleted_at timestamp with time zone,
    deleted_by uuid,
    semantic_quality_score numeric(3,2) NOT NULL,
    health_status character varying(20) DEFAULT 'unknown'::character varying NOT NULL,
    last_evaluated_at timestamp with time zone,
    auto_tier_enabled boolean DEFAULT true NOT NULL,
    name_key character varying(100) GENERATED ALWAYS AS (lower(regexp_replace((name)::text, '^r/'::text, ''::text))) STORED NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying,
    core_post_ratio numeric(5,4) DEFAULT 0,
    avg_value_score numeric(4,2) DEFAULT 0,
    recent_core_posts_30d integer DEFAULT 0,
    stats_updated_at timestamp with time zone,
    vertical character varying(50),
    history_depth_months integer DEFAULT 24,
    min_posts_target integer DEFAULT 3000,
    CONSTRAINT ck_community_pool_ck_community_pool_name_format CHECK (((name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_community_pool_name_format CHECK (((name)::text ~ '^r/[a-z0-9_]+$'::text)),
    CONSTRAINT ck_community_pool_name_len CHECK (((char_length((name)::text) >= 3) AND (char_length((name)::text) <= 100))),
    CONSTRAINT ck_community_pool_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'lab'::character varying, 'paused'::character varying, 'candidate'::character varying, 'banned'::character varying])::text[])))
);


ALTER TABLE public.community_pool OWNER TO postgres;

--
-- Name: COLUMN community_pool.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_pool.status IS '状态机: active(正常), paused(暂缓), banned(拉黑)';


--
-- Name: COLUMN community_pool.core_post_ratio; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_pool.core_post_ratio IS '含金量: Core贴占比 (0.0-1.0)';


--
-- Name: COLUMN community_pool.avg_value_score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_pool.avg_value_score IS '平均价值分 (0-10)';


--
-- Name: COLUMN community_pool.recent_core_posts_30d; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_pool.recent_core_posts_30d IS '最近30天产出的Core贴数量';


--
-- Name: community_pool_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.community_pool_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_pool_id_seq OWNER TO postgres;

--
-- Name: community_pool_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.community_pool_id_seq OWNED BY public.community_pool.id;


--
-- Name: community_roles_map; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_roles_map (
    subreddit character varying(100) NOT NULL,
    role character varying(50)
);


ALTER TABLE public.community_roles_map OWNER TO postgres;

--
-- Name: content_entities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.content_entities (
    id bigint NOT NULL,
    content_type character varying(7) NOT NULL,
    content_id bigint NOT NULL,
    entity character varying(255) NOT NULL,
    entity_type character varying(8) DEFAULT 'other'::character varying NOT NULL,
    count integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_model character varying(50) DEFAULT 'unknown'::character varying,
    feature_version integer DEFAULT 1
);


ALTER TABLE public.content_entities OWNER TO postgres;

--
-- Name: COLUMN content_entities.source_model; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.content_entities.source_model IS '实体抽取模型';


--
-- Name: COLUMN content_entities.feature_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.content_entities.feature_version IS '实体抽取版本号';


--
-- Name: content_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.content_entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.content_entities_id_seq OWNER TO postgres;

--
-- Name: content_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.content_entities_id_seq OWNED BY public.content_entities.id;


--
-- Name: content_labels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.content_labels (
    id bigint NOT NULL,
    content_type character varying(7) NOT NULL,
    content_id bigint NOT NULL,
    category character varying(255) NOT NULL,
    aspect character varying(255) DEFAULT 'other'::character varying NOT NULL,
    confidence integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    sentiment_score double precision,
    sentiment_label character varying(20),
    source_model character varying(50) DEFAULT 'unknown'::character varying,
    feature_version integer DEFAULT 1
);


ALTER TABLE public.content_labels OWNER TO postgres;

--
-- Name: COLUMN content_labels.source_model; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.content_labels.source_model IS '标签来源模型 (e.g. gemini-1.5-flash)';


--
-- Name: COLUMN content_labels.feature_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.content_labels.feature_version IS '标签体系版本号';


--
-- Name: content_labels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.content_labels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.content_labels_id_seq OWNER TO postgres;

--
-- Name: content_labels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.content_labels_id_seq OWNED BY public.content_labels.id;


--
-- Name: crawl_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawl_metrics (
    id integer NOT NULL,
    metric_date date NOT NULL,
    metric_hour integer NOT NULL,
    cache_hit_rate numeric(5,2) NOT NULL,
    valid_posts_24h integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    total_communities integer NOT NULL,
    successful_crawls integer NOT NULL,
    empty_crawls integer NOT NULL,
    failed_crawls integer NOT NULL,
    avg_latency_seconds numeric(7,2) NOT NULL,
    total_new_posts integer NOT NULL,
    total_updated_posts integer NOT NULL,
    total_duplicates integer NOT NULL,
    tier_assignments json,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    crawl_run_id uuid
);


ALTER TABLE public.crawl_metrics OWNER TO postgres;

--
-- Name: crawl_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crawl_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.crawl_metrics_id_seq OWNER TO postgres;

--
-- Name: crawl_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crawl_metrics_id_seq OWNED BY public.crawl_metrics.id;


--
-- Name: crawler_run_targets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawler_run_targets (
    id uuid NOT NULL,
    crawl_run_id uuid NOT NULL,
    subreddit text NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    status character varying(20) DEFAULT 'running'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_code character varying(120),
    error_message_short text,
    plan_kind character varying(32),
    idempotency_key text,
    idempotency_key_human text
);


ALTER TABLE public.crawler_run_targets OWNER TO postgres;

--
-- Name: crawler_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawler_runs (
    id uuid NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    status character varying(20) DEFAULT 'running'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE public.crawler_runs OWNER TO postgres;

--
-- Name: data_audit_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.data_audit_events (
    id bigint NOT NULL,
    event_type character varying(50) NOT NULL,
    target_type character varying(20) NOT NULL,
    target_id character varying(100) NOT NULL,
    old_value jsonb,
    new_value jsonb,
    reason text,
    source_component character varying(50),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.data_audit_events OWNER TO postgres;

--
-- Name: TABLE data_audit_events; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.data_audit_events IS '统一数据审计表：记录数据生命周期中的关键变动 (Promote/Demote/Reject)';


--
-- Name: data_audit_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.data_audit_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.data_audit_events_id_seq OWNER TO postgres;

--
-- Name: data_audit_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.data_audit_events_id_seq OWNED BY public.data_audit_events.id;


--
-- Name: discovered_communities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.discovered_communities (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    discovered_from_keywords jsonb,
    discovered_count integer DEFAULT 1 NOT NULL,
    first_discovered_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_discovered_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    admin_reviewed_at timestamp with time zone,
    admin_notes text,
    discovered_from_task_id uuid,
    reviewed_by uuid,
    created_by uuid,
    updated_by uuid,
    deleted_at timestamp with time zone,
    deleted_by uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL,
    tags character varying[] DEFAULT '{}'::character varying[] NOT NULL,
    cooldown_until timestamp with time zone,
    rejection_count integer DEFAULT 0 NOT NULL,
    CONSTRAINT ck_pending_communities_ck_pending_communities_name_format CHECK (((name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_pending_communities_ck_pending_communities_name_len CHECK (((char_length((name)::text) >= 3) AND (char_length((name)::text) <= 100))),
    CONSTRAINT ck_pending_communities_name_format CHECK (((name)::text ~ '^r/[a-zA-Z0-9_]+$'::text))
);


ALTER TABLE public.discovered_communities OWNER TO postgres;

--
-- Name: discovered_communities_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.discovered_communities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.discovered_communities_id_seq OWNER TO postgres;

--
-- Name: discovered_communities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.discovered_communities_id_seq OWNED BY public.discovered_communities.id;


--
-- Name: evidence_posts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evidence_posts (
    id integer NOT NULL,
    crawl_run_id uuid,
    target_id uuid,
    probe_source character varying(20) NOT NULL,
    source_query text,
    source_query_hash character varying(64) NOT NULL,
    source_post_id character varying(100) NOT NULL,
    subreddit character varying(100) NOT NULL,
    title text NOT NULL,
    summary text,
    score integer DEFAULT 0 NOT NULL,
    num_comments integer DEFAULT 0 NOT NULL,
    post_created_at timestamp with time zone,
    evidence_score integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.evidence_posts OWNER TO postgres;

--
-- Name: evidence_posts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.evidence_posts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.evidence_posts_id_seq OWNER TO postgres;

--
-- Name: evidence_posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.evidence_posts_id_seq OWNED BY public.evidence_posts.id;


--
-- Name: evidences; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evidences (
    id uuid NOT NULL,
    insight_card_id uuid NOT NULL,
    post_url character varying(500) NOT NULL,
    excerpt text NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    subreddit character varying(100) NOT NULL,
    score numeric(5,4) DEFAULT 0.0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_evidences_score_range CHECK (((score >= 0.0) AND (score <= 1.0)))
);


ALTER TABLE public.evidences OWNER TO postgres;

--
-- Name: COLUMN evidences.post_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.evidences.post_url IS '原帖 URL';


--
-- Name: COLUMN evidences.excerpt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.evidences.excerpt IS '摘录内容';


--
-- Name: COLUMN evidences."timestamp"; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.evidences."timestamp" IS '帖子时间戳';


--
-- Name: COLUMN evidences.subreddit; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.evidences.subreddit IS '子版块名称';


--
-- Name: COLUMN evidences.score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.evidences.score IS '证据分数 (0.0-1.0)';


--
-- Name: facts_quality_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.facts_quality_audit (
    run_id uuid NOT NULL,
    topic text NOT NULL,
    days integer NOT NULL,
    mode text NOT NULL,
    config_hash text,
    trend_source text,
    trend_degraded boolean,
    time_window_used integer,
    comments_count integer,
    posts_count integer,
    solutions_count integer,
    community_coverage integer,
    degraded boolean,
    data_fallback boolean,
    posts_fallback boolean,
    solutions_fallback boolean,
    dynamic_whitelist jsonb,
    dynamic_blacklist jsonb,
    insufficient_flags jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.facts_quality_audit OWNER TO postgres;

--
-- Name: facts_run_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.facts_run_logs (
    id uuid NOT NULL,
    task_id uuid NOT NULL,
    audit_level character varying(20) DEFAULT 'lab'::character varying NOT NULL,
    status character varying(20) DEFAULT 'ok'::character varying NOT NULL,
    validator_level character varying(10) DEFAULT 'info'::character varying NOT NULL,
    retention_days integer DEFAULT 7 NOT NULL,
    expires_at timestamp with time zone,
    summary jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_code character varying(120),
    error_message_short text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_facts_run_logs_ck_facts_run_logs_valid_audit_level CHECK (((audit_level)::text = ANY ((ARRAY['gold'::character varying, 'lab'::character varying, 'noise'::character varying])::text[]))),
    CONSTRAINT ck_facts_run_logs_ck_facts_run_logs_valid_status CHECK (((status)::text = ANY ((ARRAY['ok'::character varying, 'blocked'::character varying, 'failed'::character varying, 'skipped'::character varying])::text[]))),
    CONSTRAINT ck_facts_run_logs_ck_facts_run_logs_valid_validator_level CHECK (((validator_level)::text = ANY ((ARRAY['info'::character varying, 'warn'::character varying, 'error'::character varying])::text[])))
);


ALTER TABLE public.facts_run_logs OWNER TO postgres;

--
-- Name: COLUMN facts_run_logs.task_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.task_id IS '关联的分析任务 ID';


--
-- Name: COLUMN facts_run_logs.audit_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.audit_level IS '审计档位：gold/lab/noise';


--
-- Name: COLUMN facts_run_logs.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.status IS '运行状态：ok/blocked/failed/skipped';


--
-- Name: COLUMN facts_run_logs.validator_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.validator_level IS 'validator 级别：info/warn/error';


--
-- Name: COLUMN facts_run_logs.retention_days; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.retention_days IS '日志保留天数（默认 7 天）';


--
-- Name: COLUMN facts_run_logs.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.expires_at IS '日志过期时间（UTC）';


--
-- Name: COLUMN facts_run_logs.summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.summary IS '最小运行摘要（计数/配置/范围等）';


--
-- Name: COLUMN facts_run_logs.error_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.error_code IS '失败/拦截错误码';


--
-- Name: COLUMN facts_run_logs.error_message_short; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_run_logs.error_message_short IS '一行错误摘要';


--
-- Name: facts_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.facts_snapshots (
    id uuid NOT NULL,
    task_id uuid NOT NULL,
    schema_version character varying(10) DEFAULT '2.0'::character varying NOT NULL,
    v2_package jsonb DEFAULT '{}'::jsonb NOT NULL,
    quality jsonb DEFAULT '{}'::jsonb NOT NULL,
    passed boolean DEFAULT false NOT NULL,
    tier character varying(20) DEFAULT 'C_scouting'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    audit_level character varying(20) DEFAULT 'lab'::character varying NOT NULL,
    status character varying(20) DEFAULT 'ok'::character varying NOT NULL,
    validator_level character varying(10) DEFAULT 'info'::character varying NOT NULL,
    retention_days integer DEFAULT 30 NOT NULL,
    expires_at timestamp with time zone,
    blocked_reason character varying(120),
    error_code character varying(120),
    CONSTRAINT ck_facts_snapshots_ck_facts_snapshots_schema_version_non_empty CHECK (((schema_version)::text <> ''::text)),
    CONSTRAINT ck_facts_snapshots_ck_facts_snapshots_valid_audit_level CHECK (((audit_level)::text = ANY ((ARRAY['gold'::character varying, 'lab'::character varying, 'noise'::character varying])::text[]))),
    CONSTRAINT ck_facts_snapshots_ck_facts_snapshots_valid_status CHECK (((status)::text = ANY ((ARRAY['ok'::character varying, 'blocked'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_facts_snapshots_ck_facts_snapshots_valid_tier CHECK (((tier)::text = ANY ((ARRAY['A_full'::character varying, 'B_trimmed'::character varying, 'C_scouting'::character varying, 'X_blocked'::character varying])::text[]))),
    CONSTRAINT ck_facts_snapshots_ck_facts_snapshots_valid_validator_level CHECK (((validator_level)::text = ANY ((ARRAY['info'::character varying, 'warn'::character varying, 'error'::character varying])::text[])))
);


ALTER TABLE public.facts_snapshots OWNER TO postgres;

--
-- Name: COLUMN facts_snapshots.task_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_snapshots.task_id IS '关联的分析任务 ID';


--
-- Name: COLUMN facts_snapshots.schema_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_snapshots.schema_version IS 'facts_v2 schema version';


--
-- Name: COLUMN facts_snapshots.v2_package; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_snapshots.v2_package IS 'facts_v2 审计包（v2_package）';


--
-- Name: COLUMN facts_snapshots.quality; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_snapshots.quality IS '质量闸门结果（passed/tier/flags/metrics + 其它校验信息）';


--
-- Name: COLUMN facts_snapshots.passed; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_snapshots.passed IS '是否通过质量闸门（tier != X_blocked）';


--
-- Name: COLUMN facts_snapshots.tier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.facts_snapshots.tier IS '报告等级：A_full/B_trimmed/C_scouting/X_blocked';


--
-- Name: feedback_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source text NOT NULL,
    event_type text NOT NULL,
    user_id text,
    task_id text,
    analysis_id text,
    payload jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_feedback_event_type CHECK ((event_type = ANY (ARRAY['community_decision'::text, 'analysis_rating'::text, 'insight_flag'::text, 'metric'::text]))),
    CONSTRAINT ck_feedback_source CHECK ((source = ANY (ARRAY['user'::text, 'admin'::text, 'system'::text])))
);


ALTER TABLE public.feedback_events OWNER TO postgres;

--
-- Name: insight_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.insight_cards (
    id uuid NOT NULL,
    task_id uuid NOT NULL,
    title character varying(500) NOT NULL,
    summary text NOT NULL,
    confidence numeric(5,4) NOT NULL,
    time_window_days integer DEFAULT 30 NOT NULL,
    subreddits character varying(100)[] DEFAULT '{}'::character varying[] NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_insight_cards_ck_insight_cards_confidence_range CHECK (((confidence >= 0.0) AND (confidence <= 1.0))),
    CONSTRAINT ck_insight_cards_ck_insight_cards_time_window_positive CHECK ((time_window_days > 0))
);


ALTER TABLE public.insight_cards OWNER TO postgres;

--
-- Name: COLUMN insight_cards.title; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.insight_cards.title IS '洞察卡片标题';


--
-- Name: COLUMN insight_cards.summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.insight_cards.summary IS '洞察摘要';


--
-- Name: COLUMN insight_cards.confidence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.insight_cards.confidence IS '置信度分数 (0.0-1.0)';


--
-- Name: COLUMN insight_cards.time_window_days; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.insight_cards.time_window_days IS '时间窗口（天数）';


--
-- Name: COLUMN insight_cards.subreddits; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.insight_cards.subreddits IS '相关子版块列表';


--
-- Name: maintenance_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.maintenance_audit (
    id bigint NOT NULL,
    task_name character varying(128) NOT NULL,
    source character varying(32),
    triggered_by character varying(128),
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ended_at timestamp with time zone,
    affected_rows integer DEFAULT 0 NOT NULL,
    sample_ids bigint[],
    extra jsonb
);


ALTER TABLE public.maintenance_audit OWNER TO postgres;

--
-- Name: maintenance_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.maintenance_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.maintenance_audit_id_seq OWNER TO postgres;

--
-- Name: maintenance_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.maintenance_audit_id_seq OWNED BY public.maintenance_audit.id;


--
-- Name: posts_raw; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts_raw (
    id bigint NOT NULL,
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone NOT NULL,
    fetched_at timestamp with time zone DEFAULT now() NOT NULL,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    valid_to timestamp with time zone DEFAULT '9999-12-31 08:00:00+08'::timestamp with time zone,
    is_current boolean DEFAULT true NOT NULL,
    author_id character varying(100),
    author_name character varying(100),
    title text NOT NULL,
    body text,
    body_norm text,
    text_norm_hash character varying(64),
    url text,
    subreddit character varying(100) NOT NULL,
    score integer DEFAULT 0,
    num_comments integer DEFAULT 0,
    is_deleted boolean DEFAULT false,
    edit_count integer DEFAULT 0,
    lang character varying(10),
    metadata jsonb,
    is_duplicate boolean DEFAULT false NOT NULL,
    duplicate_of_id bigint,
    spam_category character varying(50),
    value_score smallint,
    business_pool character varying(10),
    community_id integer,
    score_source character varying(50),
    score_version integer DEFAULT 1,
    first_seen_at timestamp with time zone DEFAULT now(),
    source_track character varying(32) DEFAULT 'incremental'::character varying,
    crawl_run_id uuid,
    community_run_id uuid,
    CONSTRAINT ck_posts_raw_business_pool CHECK (((business_pool)::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying])::text[]))),
    CONSTRAINT ck_posts_raw_subreddit_format CHECK (((subreddit)::text ~ '^r/[a-z0-9_]+$'::text)),
    CONSTRAINT ck_posts_raw_valid_period CHECK (((valid_from < valid_to) OR (valid_to = '9999-12-31 00:00:00'::timestamp without time zone))),
    CONSTRAINT ck_posts_raw_version_positive CHECK ((version > 0))
);


ALTER TABLE public.posts_raw OWNER TO postgres;

--
-- Name: TABLE posts_raw; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posts_raw IS '冷库：增量累积，保留90天滚动窗口，用于算法训练、趋势分析、回测';


--
-- Name: COLUMN posts_raw.version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.version IS 'SCD2: 版本号，每次编辑+1';


--
-- Name: COLUMN posts_raw.is_current; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.is_current IS 'SCD2: 是否当前版本';


--
-- Name: COLUMN posts_raw.text_norm_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.text_norm_hash IS '文本归一化哈希，用于去重（防止转贴/改写）';


--
-- Name: COLUMN posts_raw.metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.metadata IS 'JSONB 扩展字段。
关键 Key 定义:
- value_tier (Layer 2 提纯):
  - gold_decision: 决策/对比/选品 (worth it, vs, recommend)
  - gold_problem: 痛点/具体问题 (how to, issue, fail)
  - gold_product: 提及具体品牌/参数
  - normal: 普通/待定 (默认)';


--
-- Name: COLUMN posts_raw.spam_category; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.spam_category IS 'Layer 2 降噪标签: 记录广告/垃圾类型。
枚举值示例: 
- ad_link_farm: 链接堆砌 (http > 2)
- ad_keywords: 包含折扣/推广词 (promo, affiliate)
- ad_short_url: 包含短链/追踪链 (bit.ly, amzn.to)
- ad_seeded: 疑似种草文/软广 (emojis + links)
- null: 正常内容';


--
-- Name: COLUMN posts_raw.business_pool; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.business_pool IS '业务分池 (The Three Pools): core (>=8, 决策用), lab (3-7, 趋势用), noise (<=2, 负样本)';


--
-- Name: COLUMN posts_raw.score_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.score_source IS '打分来源: rule_vX, ai_gemini_vX, manual';


--
-- Name: COLUMN posts_raw.score_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.score_version IS '打分规则版本号';


--
-- Name: mv_analysis_entities; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.mv_analysis_entities AS
 SELECT p.id AS post_id,
    p.subreddit,
    p.created_at,
    e.entity AS entity_name,
    e.entity_type
   FROM (public.content_entities e
     JOIN public.posts_raw p ON ((e.content_id = p.id)))
  WHERE ((e.content_type)::text = 'post'::text)
UNION ALL
 SELECT c.id AS post_id,
    c.subreddit,
    c.created_utc AS created_at,
    e.entity AS entity_name,
    e.entity_type
   FROM (public.content_entities e
     JOIN public.comments c ON ((e.content_id = c.id)))
  WHERE ((e.content_type)::text = 'comment'::text)
  WITH NO DATA;


ALTER TABLE public.mv_analysis_entities OWNER TO postgres;

--
-- Name: mv_analysis_labels; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.mv_analysis_labels AS
 SELECT p.id AS post_id,
    p.subreddit,
    p.created_at,
    p.score,
    p.num_comments,
    l.category,
    l.aspect,
    (l.sentiment_label)::text AS sentiment,
    l.sentiment_score,
    l.confidence
   FROM (public.content_labels l
     JOIN public.posts_raw p ON ((l.content_id = p.id)))
  WHERE ((l.content_type)::text = 'post'::text)
UNION ALL
 SELECT c.id AS post_id,
    c.subreddit,
    c.created_utc AS created_at,
    c.score,
    0 AS num_comments,
    l.category,
    l.aspect,
    (l.sentiment_label)::text AS sentiment,
    l.sentiment_score,
    l.confidence
   FROM (public.content_labels l
     JOIN public.comments c ON ((l.content_id = c.id)))
  WHERE ((l.content_type)::text = 'comment'::text)
  WITH NO DATA;


ALTER TABLE public.mv_analysis_labels OWNER TO postgres;

--
-- Name: mv_monthly_trend; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.mv_monthly_trend AS
 WITH monthly AS (
         SELECT (date_trunc('month'::text, posts_raw.created_at))::date AS month_start,
            count(*) AS posts_cnt,
            (0)::bigint AS comments_cnt,
            sum(posts_raw.score) AS score_sum
           FROM public.posts_raw
          WHERE ((posts_raw.is_current = true) AND ((posts_raw.business_pool)::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying])::text[])))
          GROUP BY ((date_trunc('month'::text, posts_raw.created_at))::date)
        UNION ALL
         SELECT (date_trunc('month'::text, c.created_utc))::date AS month_start,
            (0)::bigint AS posts_cnt,
            count(*) AS comments_cnt,
            sum(c.score) AS score_sum
           FROM (public.comments c
             JOIN public.posts_raw p ON ((c.post_id = p.id)))
          WHERE ((p.business_pool)::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying])::text[]))
          GROUP BY ((date_trunc('month'::text, c.created_utc))::date)
        ), agg AS (
         SELECT monthly.month_start,
            sum(monthly.posts_cnt) AS posts_cnt,
            sum(monthly.comments_cnt) AS comments_cnt,
            sum(monthly.score_sum) AS score_sum
           FROM monthly
          GROUP BY monthly.month_start
        )
 SELECT agg.month_start,
    agg.posts_cnt,
    agg.comments_cnt,
    agg.score_sum,
    (agg.posts_cnt - lag(agg.posts_cnt) OVER (ORDER BY agg.month_start)) AS posts_velocity_mom,
    (agg.comments_cnt - lag(agg.comments_cnt) OVER (ORDER BY agg.month_start)) AS comments_velocity_mom,
    (agg.score_sum - lag(agg.score_sum) OVER (ORDER BY agg.month_start)) AS score_velocity_mom
   FROM agg
  ORDER BY agg.month_start
  WITH NO DATA;


ALTER TABLE public.mv_monthly_trend OWNER TO postgres;

--
-- Name: noise_labels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.noise_labels (
    id integer NOT NULL,
    content_type text NOT NULL,
    content_id bigint NOT NULL,
    noise_type text NOT NULL,
    reason text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT noise_labels_content_type_check CHECK ((content_type = ANY (ARRAY['post'::text, 'comment'::text]))),
    CONSTRAINT noise_labels_noise_type_check CHECK ((noise_type = ANY (ARRAY['employee_rant'::text, 'resale'::text, 'bot'::text, 'automod'::text, 'template'::text, 'spam_manual'::text, 'offtopic'::text, 'low_quality'::text, 'pure_social'::text, 'rage_rant'::text, 'meme_only'::text, 'ultra_short'::text])))
);


ALTER TABLE public.noise_labels OWNER TO postgres;

--
-- Name: TABLE noise_labels; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.noise_labels IS '负样本金库：用于存储和训练的已标记噪音数据';


--
-- Name: noise_labels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.noise_labels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.noise_labels_id_seq OWNER TO postgres;

--
-- Name: noise_labels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.noise_labels_id_seq OWNED BY public.noise_labels.id;


--
-- Name: post_comment_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.post_comment_stats AS
 SELECT comments.post_id,
    count(*) AS comment_count,
    avg(comments.score) AS avg_reddit_score,
    sum(comments.awards_count) AS total_awards,
    count(*) FILTER (WHERE (length(comments.body) > 150)) AS long_comment_count,
    count(*) FILTER (WHERE (comments.body ~* '\?|\b(how|what|why|where)\b'::text)) AS qa_comment_count,
    count(*) FILTER (WHERE (comments.body ~* '\b(fixed|solution|solved|bought|ordered|recommend|works well|use this)\b'::text)) AS solution_comment_count,
    max(comments.value_score) AS max_value_score,
    count(*) FILTER (WHERE (comments.value_score >= 8)) AS core_comment_count
   FROM public.comments
  GROUP BY comments.post_id
  WITH NO DATA;


ALTER TABLE public.post_comment_stats OWNER TO postgres;

--
-- Name: post_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.post_embeddings (
    post_id bigint NOT NULL,
    model_version character varying(50) DEFAULT 'BAAI/bge-m3'::character varying NOT NULL,
    embedding public.vector(1024),
    created_at timestamp with time zone DEFAULT now(),
    source_model character varying(50) DEFAULT 'BAAI/bge-m3'::character varying,
    feature_version integer DEFAULT 1
);


ALTER TABLE public.post_embeddings OWNER TO postgres;

--
-- Name: COLUMN post_embeddings.source_model; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.post_embeddings.source_model IS '向量模型名称';


--
-- Name: COLUMN post_embeddings.feature_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.post_embeddings.feature_version IS '向量版本号';


--
-- Name: post_scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.post_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    post_id bigint NOT NULL,
    llm_version character varying(50) NOT NULL,
    rule_version character varying(50) NOT NULL,
    scored_at timestamp with time zone DEFAULT now(),
    is_latest boolean DEFAULT true,
    value_score numeric(4,2),
    opportunity_score numeric(4,2),
    business_pool character varying(20),
    sentiment numeric(4,3),
    purchase_intent_score numeric(4,2),
    tags_analysis jsonb DEFAULT '{}'::jsonb,
    entities_extracted jsonb DEFAULT '[]'::jsonb,
    calculation_log jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT post_scores_business_pool_check CHECK (((business_pool)::text = ANY ((ARRAY['core'::character varying, 'lab'::character varying, 'noise'::character varying])::text[])))
);


ALTER TABLE public.post_scores OWNER TO postgres;

--
-- Name: post_scores_latest_v; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.post_scores_latest_v AS
 WITH has_primary AS (
         SELECT (EXISTS ( SELECT 1
                   FROM public.post_scores post_scores_1
                  WHERE ((post_scores_1.is_latest = true) AND ((post_scores_1.rule_version)::text <> 'rulebook_v1'::text)))) AS has_primary
        )
 SELECT post_scores.id,
    post_scores.post_id,
    post_scores.llm_version,
    post_scores.rule_version,
    post_scores.scored_at,
    post_scores.is_latest,
    post_scores.value_score,
    post_scores.opportunity_score,
    post_scores.business_pool,
    post_scores.sentiment,
    post_scores.purchase_intent_score,
    post_scores.tags_analysis,
    post_scores.entities_extracted,
    post_scores.calculation_log
   FROM public.post_scores,
    has_primary
  WHERE ((post_scores.is_latest = true) AND (((has_primary.has_primary = false) AND ((post_scores.rule_version)::text = 'rulebook_v1'::text)) OR ((has_primary.has_primary = true) AND ((post_scores.rule_version)::text <> 'rulebook_v1'::text))));


ALTER TABLE public.post_scores_latest_v OWNER TO postgres;

--
-- Name: post_semantic_labels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.post_semantic_labels (
    id bigint NOT NULL,
    post_id bigint NOT NULL,
    l1_category character varying(50),
    l2_business character varying(50),
    l3_scene character varying(100),
    matched_rule_ids integer[],
    top_terms text[],
    raw_scores json,
    sentiment_score double precision,
    confidence double precision,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    l1_secondary character varying(50),
    tags character varying(50)[]
);


ALTER TABLE public.post_semantic_labels OWNER TO postgres;

--
-- Name: post_semantic_labels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.post_semantic_labels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.post_semantic_labels_id_seq OWNER TO postgres;

--
-- Name: post_semantic_labels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.post_semantic_labels_id_seq OWNED BY public.post_semantic_labels.id;


--
-- Name: posts_archive; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts_archive (
    id bigint NOT NULL,
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    archived_at timestamp with time zone DEFAULT now() NOT NULL,
    payload jsonb NOT NULL
);


ALTER TABLE public.posts_archive OWNER TO postgres;

--
-- Name: posts_archive_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posts_archive_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posts_archive_id_seq OWNER TO postgres;

--
-- Name: posts_archive_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posts_archive_id_seq OWNED BY public.posts_archive.id;


--
-- Name: posts_hot_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posts_hot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posts_hot_id_seq OWNER TO postgres;

--
-- Name: posts_hot; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts_hot (
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    cached_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '180 days'::interval) NOT NULL,
    title text NOT NULL,
    body text,
    subreddit character varying(100) NOT NULL,
    score integer DEFAULT 0,
    num_comments integer DEFAULT 0,
    metadata jsonb,
    id bigint DEFAULT nextval('public.posts_hot_id_seq'::regclass) NOT NULL,
    author_id character varying(100),
    author_name character varying(100),
    content_labels jsonb,
    entities jsonb,
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, ((COALESCE(title, ''::text) || ' '::text) || COALESCE(body, ''::text)))) STORED,
    CONSTRAINT ck_posts_hot_subreddit_format CHECK (((subreddit)::text ~ '^r/[a-z0-9_]+$'::text))
);


ALTER TABLE public.posts_hot OWNER TO postgres;

--
-- Name: TABLE posts_hot; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posts_hot IS '热缓存：覆盖式刷新，保留24-72小时，用于实时分析';


--
-- Name: posts_latest; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.posts_latest AS
 SELECT p.id,
    p.source,
    p.source_post_id,
    p.version,
    p.created_at,
    p.fetched_at,
    p.valid_from,
    p.valid_to,
    p.is_current,
    p.author_id,
    p.author_name,
    p.title,
    p.body,
    p.body_norm,
    p.text_norm_hash,
    p.url,
    p.subreddit,
    p.community_id,
    p.score,
    p.num_comments,
    p.is_deleted,
    p.edit_count,
    p.lang,
    p.metadata,
    p.value_score,
    p.business_pool,
    p.score_source,
    p.score_version
   FROM public.posts_raw p
  WHERE (p.is_current = true)
  WITH NO DATA;


ALTER TABLE public.posts_latest OWNER TO postgres;

--
-- Name: posts_quarantine; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts_quarantine (
    id bigint NOT NULL,
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    subreddit character varying(100),
    title text,
    body text,
    author_name character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    rejected_at timestamp with time zone DEFAULT now(),
    reject_reason text,
    original_payload jsonb
);


ALTER TABLE public.posts_quarantine OWNER TO postgres;

--
-- Name: TABLE posts_quarantine; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posts_quarantine IS '小黑屋：存储被触发器拦截的低质量/不合规内容 (Ghost/Short/Blocked)';


--
-- Name: posts_quarantine_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posts_quarantine_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posts_quarantine_id_seq OWNER TO postgres;

--
-- Name: posts_quarantine_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posts_quarantine_id_seq OWNED BY public.posts_quarantine.id;


--
-- Name: posts_raw_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posts_raw_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posts_raw_id_seq OWNER TO postgres;

--
-- Name: posts_raw_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posts_raw_id_seq OWNED BY public.posts_raw.id;


--
-- Name: quality_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quality_metrics (
    id integer NOT NULL,
    date date NOT NULL,
    collection_success_rate numeric(5,4) NOT NULL,
    deduplication_rate numeric(5,4) NOT NULL,
    processing_time_p50 numeric(7,2) NOT NULL,
    processing_time_p95 numeric(7,2) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_quality_metrics_collection_rate_range CHECK (((collection_success_rate >= 0.00) AND (collection_success_rate <= 1.00))),
    CONSTRAINT ck_quality_metrics_dedup_rate_range CHECK (((deduplication_rate >= 0.00) AND (deduplication_rate <= 1.00))),
    CONSTRAINT ck_quality_metrics_p50_positive CHECK ((processing_time_p50 >= (0)::numeric)),
    CONSTRAINT ck_quality_metrics_p95_gte_p50 CHECK ((processing_time_p95 >= processing_time_p50)),
    CONSTRAINT ck_quality_metrics_p95_positive CHECK ((processing_time_p95 >= (0)::numeric))
);


ALTER TABLE public.quality_metrics OWNER TO postgres;

--
-- Name: quality_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quality_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.quality_metrics_id_seq OWNER TO postgres;

--
-- Name: quality_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quality_metrics_id_seq OWNED BY public.quality_metrics.id;


--
-- Name: reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    analysis_id uuid NOT NULL,
    html_content text NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    template_version character varying(10) DEFAULT '1.0'::character varying NOT NULL,
    generated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_reports_html_size CHECK ((length(html_content) <= 10485760)),
    CONSTRAINT ck_reports_status CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('deprecated'::character varying)::text, ('draft'::character varying)::text])))
);


ALTER TABLE public.reports OWNER TO postgres;

--
-- Name: semantic_audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semantic_audit_logs (
    id integer NOT NULL,
    action character varying(32) NOT NULL,
    entity_type character varying(32) NOT NULL,
    entity_id bigint NOT NULL,
    changes jsonb,
    operator_id uuid,
    operator_ip character varying(45),
    reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.semantic_audit_logs OWNER TO postgres;

--
-- Name: semantic_audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semantic_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semantic_audit_logs_id_seq OWNER TO postgres;

--
-- Name: semantic_audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semantic_audit_logs_id_seq OWNED BY public.semantic_audit_logs.id;


--
-- Name: semantic_candidates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semantic_candidates (
    id integer NOT NULL,
    term character varying(128) NOT NULL,
    frequency integer NOT NULL,
    source character varying(16) NOT NULL,
    first_seen_at timestamp with time zone NOT NULL,
    last_seen_at timestamp with time zone NOT NULL,
    status character varying(16) NOT NULL,
    reviewed_by uuid,
    reviewed_at timestamp with time zone,
    reject_reason text,
    approved_category character varying(32),
    approved_layer character varying(8),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT ck_semantic_candidates_ck_semantic_candidates_status_valid CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('approved'::character varying)::text, ('rejected'::character varying)::text])))
);


ALTER TABLE public.semantic_candidates OWNER TO postgres;

--
-- Name: semantic_candidates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semantic_candidates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semantic_candidates_id_seq OWNER TO postgres;

--
-- Name: semantic_candidates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semantic_candidates_id_seq OWNED BY public.semantic_candidates.id;


--
-- Name: semantic_concepts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semantic_concepts (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    domain character varying(50) DEFAULT 'general'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.semantic_concepts OWNER TO postgres;

--
-- Name: semantic_concepts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semantic_concepts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semantic_concepts_id_seq OWNER TO postgres;

--
-- Name: semantic_concepts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semantic_concepts_id_seq OWNED BY public.semantic_concepts.id;


--
-- Name: semantic_rules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semantic_rules (
    id integer NOT NULL,
    concept_id integer NOT NULL,
    term character varying(255) NOT NULL,
    rule_type character varying(20) DEFAULT 'keyword'::character varying NOT NULL,
    weight numeric(5,2) DEFAULT 1.0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    hit_count integer DEFAULT 0 NOT NULL,
    last_hit_at timestamp with time zone,
    meta json DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    domain character varying(50),
    aspect character varying(50),
    source character varying(20) DEFAULT 'yaml'::character varying
);


ALTER TABLE public.semantic_rules OWNER TO postgres;

--
-- Name: semantic_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semantic_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semantic_rules_id_seq OWNER TO postgres;

--
-- Name: semantic_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semantic_rules_id_seq OWNED BY public.semantic_rules.id;


--
-- Name: semantic_terms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semantic_terms (
    id bigint NOT NULL,
    canonical character varying(128) NOT NULL,
    aliases character varying(128)[],
    category character varying(32) NOT NULL,
    layer character varying(8),
    precision_tag character varying(16),
    weight numeric(10,4),
    polarity character varying(16),
    lifecycle character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.semantic_terms OWNER TO postgres;

--
-- Name: semantic_terms_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.semantic_terms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semantic_terms_id_seq OWNER TO postgres;

--
-- Name: semantic_terms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.semantic_terms_id_seq OWNED BY public.semantic_terms.id;


--
-- Name: storage_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.storage_metrics (
    id bigint NOT NULL,
    collected_at timestamp with time zone DEFAULT now() NOT NULL,
    posts_raw_total bigint DEFAULT '0'::bigint NOT NULL,
    posts_raw_current bigint DEFAULT '0'::bigint NOT NULL,
    posts_hot_total bigint DEFAULT '0'::bigint NOT NULL,
    posts_hot_expired bigint DEFAULT '0'::bigint NOT NULL,
    unique_subreddits bigint DEFAULT '0'::bigint NOT NULL,
    total_versions bigint DEFAULT '0'::bigint NOT NULL,
    dedup_rate numeric(5,4) DEFAULT '0'::numeric NOT NULL,
    notes jsonb
);


ALTER TABLE public.storage_metrics OWNER TO postgres;

--
-- Name: storage_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.storage_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.storage_metrics_id_seq OWNER TO postgres;

--
-- Name: storage_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.storage_metrics_id_seq OWNED BY public.storage_metrics.id;


--
-- Name: subreddit_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subreddit_snapshots (
    id bigint NOT NULL,
    subreddit character varying(100) NOT NULL,
    captured_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    subscribers character varying(32),
    active_user_count character varying(32),
    rules_text text,
    over18 boolean,
    moderation_score integer
);


ALTER TABLE public.subreddit_snapshots OWNER TO postgres;

--
-- Name: subreddit_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subreddit_snapshots_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subreddit_snapshots_id_seq OWNER TO postgres;

--
-- Name: subreddit_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subreddit_snapshots_id_seq OWNED BY public.subreddit_snapshots.id;


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    product_description text NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp with time zone,
    started_at timestamp with time zone,
    retry_count integer DEFAULT 0 NOT NULL,
    failure_category character varying(50),
    last_retry_at timestamp with time zone,
    dead_letter_at timestamp with time zone,
    mode character varying(50) DEFAULT 'market_insight'::character varying NOT NULL,
    topic_profile_id character varying(100),
    audit_level character varying(20) DEFAULT 'lab'::character varying NOT NULL,
    CONSTRAINT ck_tasks_ck_tasks_valid_audit_level CHECK (((audit_level)::text = ANY ((ARRAY['gold'::character varying, 'lab'::character varying, 'noise'::character varying])::text[]))),
    CONSTRAINT ck_tasks_ck_tasks_valid_mode CHECK (((mode)::text = ANY ((ARRAY['market_insight'::character varying, 'operations'::character varying])::text[]))),
    CONSTRAINT ck_tasks_ck_tasks_valid_topic_profile_id CHECK (((topic_profile_id IS NULL) OR ((topic_profile_id)::text <> ''::text))),
    CONSTRAINT ck_tasks_completed_status_alignment CHECK (((((status)::text = 'completed'::text) AND (completed_at IS NOT NULL)) OR (((status)::text <> 'completed'::text) AND (completed_at IS NULL)))),
    CONSTRAINT ck_tasks_completion_consistency CHECK (((((status)::text = 'completed'::text) AND (completed_at IS NOT NULL)) OR (((status)::text <> 'completed'::text) AND (completed_at IS NULL)))),
    CONSTRAINT ck_tasks_description_length CHECK (((char_length(product_description) >= 10) AND (char_length(product_description) <= 2000))),
    CONSTRAINT ck_tasks_error_length CHECK (((error_message IS NULL) OR (char_length(error_message) <= 1000))),
    CONSTRAINT ck_tasks_error_message_when_failed CHECK (((((status)::text = 'failed'::text) AND (error_message IS NOT NULL)) OR (((status)::text <> 'failed'::text) AND ((error_message IS NULL) OR (error_message = ''::text))))),
    CONSTRAINT ck_tasks_error_msg_failed CHECK (((((status)::text = 'failed'::text) AND (error_message IS NOT NULL)) OR (((status)::text <> 'failed'::text) AND ((error_message IS NULL) OR (error_message = ''::text))))),
    CONSTRAINT ck_tasks_valid_completion_time CHECK (((completed_at IS NULL) OR (started_at IS NULL) OR (completed_at >= started_at)))
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- Name: TABLE tasks; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.tasks IS '用户分析任务表 - 支持完整生命周期管理和多租户数据隔离';


--
-- Name: COLUMN tasks.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.id IS '任务唯一标识';


--
-- Name: COLUMN tasks.user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.user_id IS '任务所属用户，实现多租户隔离';


--
-- Name: COLUMN tasks.product_description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.product_description IS '用户输入的产品描述，10-2000字符';


--
-- Name: COLUMN tasks.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.status IS '任务状态：pending/processing/completed/failed';


--
-- Name: COLUMN tasks.error_message; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.error_message IS '失败时的错误详情';


--
-- Name: COLUMN tasks.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.created_at IS '任务创建时间';


--
-- Name: COLUMN tasks.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.updated_at IS '最后更新时间';


--
-- Name: COLUMN tasks.completed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tasks.completed_at IS '任务完成时间，只有completed状态时才设置';


--
-- Name: tier_audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tier_audit_logs (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    community_name character varying(100) NOT NULL,
    action character varying(50) NOT NULL,
    field_changed character varying(50) NOT NULL,
    from_value character varying(50),
    to_value character varying(50) NOT NULL,
    changed_by character varying(120) NOT NULL,
    change_source character varying(20) DEFAULT 'manual'::character varying NOT NULL,
    reason text,
    snapshot_before jsonb NOT NULL,
    snapshot_after jsonb NOT NULL,
    suggestion_id integer,
    is_rolled_back boolean DEFAULT false NOT NULL,
    rolled_back_at timestamp with time zone,
    rolled_back_by character varying(120)
);


ALTER TABLE public.tier_audit_logs OWNER TO postgres;

--
-- Name: tier_audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tier_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tier_audit_logs_id_seq OWNER TO postgres;

--
-- Name: tier_audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tier_audit_logs_id_seq OWNED BY public.tier_audit_logs.id;


--
-- Name: tier_suggestions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tier_suggestions (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    community_name character varying(100) NOT NULL,
    current_tier character varying(20) NOT NULL,
    suggested_tier character varying(20) NOT NULL,
    confidence double precision NOT NULL,
    reasons jsonb NOT NULL,
    metrics jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    generated_at timestamp with time zone DEFAULT now() NOT NULL,
    reviewed_by character varying(100),
    reviewed_at timestamp with time zone,
    applied_at timestamp with time zone,
    priority_score integer DEFAULT 0 NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.tier_suggestions OWNER TO postgres;

--
-- Name: tier_suggestions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tier_suggestions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tier_suggestions_id_seq OWNER TO postgres;

--
-- Name: tier_suggestions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tier_suggestions_id_seq OWNED BY public.tier_suggestions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(320) NOT NULL,
    password_hash character varying(255) NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    membership_level public.membership_level NOT NULL,
    CONSTRAINT ck_users_email_format CHECK (((email)::text ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text)),
    CONSTRAINT ck_users_membership_level CHECK ((membership_level = ANY (ARRAY['free'::public.membership_level, 'pro'::public.membership_level, 'enterprise'::public.membership_level]))),
    CONSTRAINT ck_users_password_hash_format CHECK ((((password_hash)::text ~ '^pbkdf2_sha256\$'::text) OR ((password_hash)::text ~ '^\$2[aby]?\$\d{2}\$'::text)))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.users IS '用户表 - 多租户架构基础，所有用户数据通过tenant_id隔离';


--
-- Name: COLUMN users.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.id IS '用户唯一标识符';


--
-- Name: COLUMN users.tenant_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.tenant_id IS '租户ID，个人用户=单用户租户';


--
-- Name: COLUMN users.email; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.email IS '用户邮箱地址，租户内唯一';


--
-- Name: COLUMN users.password_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.password_hash IS 'BCrypt密码哈希值';


--
-- Name: COLUMN users.email_verified; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.email_verified IS '邮箱是否已验证';


--
-- Name: COLUMN users.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.is_active IS '用户是否激活（软删除支持）';


--
-- Name: COLUMN users.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.created_at IS '用户创建时间';


--
-- Name: COLUMN users.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.updated_at IS '用户信息最后更新时间';


--
-- Name: v_analyses_stats; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_analyses_stats AS
 SELECT date_trunc('day'::text, analyses.created_at) AS analysis_date,
    count(*) AS total_analyses,
    avg(analyses.confidence_score) AS avg_confidence,
    min(analyses.confidence_score) AS min_confidence,
    max(analyses.confidence_score) AS max_confidence,
    avg(pg_column_size(analyses.insights)) AS avg_insights_size,
    avg(pg_column_size(analyses.sources)) AS avg_sources_size,
    count(DISTINCT analyses.analysis_version) AS version_count
   FROM public.analyses
  GROUP BY (date_trunc('day'::text, analyses.created_at))
  ORDER BY (date_trunc('day'::text, analyses.created_at)) DESC;


ALTER TABLE public.v_analyses_stats OWNER TO postgres;

--
-- Name: v_comment_semantic_tasks; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_comment_semantic_tasks AS
 SELECT c.id AS comment_id,
    c.reddit_comment_id,
    c.source_post_id,
    c.subreddit,
    "left"(c.body, 1200) AS text_for_llm,
    c.score,
    c.depth,
    c.created_utc,
    c.fetched_at,
    c.lang,
    c.source_track,
    c.first_seen_at
   FROM (public.comments c
     JOIN public.post_scores_latest_v s ON ((c.post_id = s.post_id)))
  WHERE (((s.business_pool)::text = 'core'::text) OR (s.value_score >= (6)::numeric));


ALTER TABLE public.v_comment_semantic_tasks OWNER TO postgres;

--
-- Name: vertical_map; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vertical_map (
    subreddit character varying(100) NOT NULL,
    vertical character varying(50)
);


ALTER TABLE public.vertical_map OWNER TO postgres;

--
-- Name: v_post_semantic_tasks; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_post_semantic_tasks AS
 WITH roles AS (
         SELECT lower((community_roles_map.subreddit)::text) AS subreddit,
            community_roles_map.role
           FROM public.community_roles_map
        ), verticals AS (
         SELECT lower((vertical_map.subreddit)::text) AS subreddit,
            vertical_map.vertical
           FROM public.vertical_map
        )
 SELECT p.id AS post_id,
    p.source_post_id,
    p.subreddit,
    p.title,
    "left"(p.body, 1200) AS text_for_llm,
        CASE
            WHEN (p.score >= 50) THEN 'high'::text
            WHEN (p.score >= 10) THEN 'medium'::text
            ELSE 'low'::text
        END AS score_band,
        CASE
            WHEN (p.num_comments >= 50) THEN 'high'::text
            WHEN (p.num_comments >= 5) THEN 'medium'::text
            ELSE 'low'::text
        END AS comment_band,
    r.role AS community_role,
    v.vertical,
    p.created_at,
    p.fetched_at,
    p.lang,
    p.source_track,
    p.first_seen_at
   FROM ((public.posts_raw p
     LEFT JOIN roles r ON ((lower((p.subreddit)::text) = r.subreddit)))
     LEFT JOIN verticals v ON ((lower((p.subreddit)::text) = v.subreddit)))
  WHERE (p.is_current = true);


ALTER TABLE public.v_post_semantic_tasks OWNER TO postgres;

--
-- Name: vw_community_quality; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_community_quality AS
 SELECT NULL::text AS community,
    (0.0)::double precision AS dup_ratio,
    (0.0)::double precision AS spam_ratio,
    now() AS updated_at
  WHERE false;


ALTER TABLE public.vw_community_quality OWNER TO postgres;

--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: community_audit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_audit ALTER COLUMN id SET DEFAULT nextval('public.community_audit_id_seq'::regclass);


--
-- Name: community_import_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_import_history ALTER COLUMN id SET DEFAULT nextval('public.community_import_history_id_seq'::regclass);


--
-- Name: community_pool id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool ALTER COLUMN id SET DEFAULT nextval('public.community_pool_id_seq'::regclass);


--
-- Name: content_entities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_entities ALTER COLUMN id SET DEFAULT nextval('public.content_entities_id_seq'::regclass);


--
-- Name: content_labels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_labels ALTER COLUMN id SET DEFAULT nextval('public.content_labels_id_seq'::regclass);


--
-- Name: crawl_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_metrics ALTER COLUMN id SET DEFAULT nextval('public.crawl_metrics_id_seq'::regclass);


--
-- Name: data_audit_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.data_audit_events ALTER COLUMN id SET DEFAULT nextval('public.data_audit_events_id_seq'::regclass);


--
-- Name: discovered_communities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities ALTER COLUMN id SET DEFAULT nextval('public.discovered_communities_id_seq'::regclass);


--
-- Name: evidence_posts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence_posts ALTER COLUMN id SET DEFAULT nextval('public.evidence_posts_id_seq'::regclass);


--
-- Name: maintenance_audit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.maintenance_audit ALTER COLUMN id SET DEFAULT nextval('public.maintenance_audit_id_seq'::regclass);


--
-- Name: noise_labels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.noise_labels ALTER COLUMN id SET DEFAULT nextval('public.noise_labels_id_seq'::regclass);


--
-- Name: post_semantic_labels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_semantic_labels ALTER COLUMN id SET DEFAULT nextval('public.post_semantic_labels_id_seq'::regclass);


--
-- Name: posts_archive id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_archive ALTER COLUMN id SET DEFAULT nextval('public.posts_archive_id_seq'::regclass);


--
-- Name: posts_quarantine id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_quarantine ALTER COLUMN id SET DEFAULT nextval('public.posts_quarantine_id_seq'::regclass);


--
-- Name: posts_raw id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw ALTER COLUMN id SET DEFAULT nextval('public.posts_raw_id_seq'::regclass);


--
-- Name: quality_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quality_metrics ALTER COLUMN id SET DEFAULT nextval('public.quality_metrics_id_seq'::regclass);


--
-- Name: semantic_audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.semantic_audit_logs_id_seq'::regclass);


--
-- Name: semantic_candidates id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_candidates ALTER COLUMN id SET DEFAULT nextval('public.semantic_candidates_id_seq'::regclass);


--
-- Name: semantic_concepts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_concepts ALTER COLUMN id SET DEFAULT nextval('public.semantic_concepts_id_seq'::regclass);


--
-- Name: semantic_rules id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_rules ALTER COLUMN id SET DEFAULT nextval('public.semantic_rules_id_seq'::regclass);


--
-- Name: semantic_terms id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_terms ALTER COLUMN id SET DEFAULT nextval('public.semantic_terms_id_seq'::regclass);


--
-- Name: storage_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.storage_metrics ALTER COLUMN id SET DEFAULT nextval('public.storage_metrics_id_seq'::regclass);


--
-- Name: subreddit_snapshots id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subreddit_snapshots ALTER COLUMN id SET DEFAULT nextval('public.subreddit_snapshots_id_seq'::regclass);


--
-- Name: tier_audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tier_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.tier_audit_logs_id_seq'::regclass);


--
-- Name: tier_suggestions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tier_suggestions ALTER COLUMN id SET DEFAULT nextval('public.tier_suggestions_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: analyses analyses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT analyses_pkey PRIMARY KEY (id);


--
-- Name: analytics_community_history analytics_community_history_pkey; Type: CONSTRAINT; Schema: public; Owner: hujia
--

ALTER TABLE ONLY public.analytics_community_history
    ADD CONSTRAINT analytics_community_history_pkey PRIMARY KEY (report_date, subreddit);


--
-- Name: beta_feedback beta_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.beta_feedback
    ADD CONSTRAINT beta_feedback_pkey PRIMARY KEY (id);


--
-- Name: business_categories business_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_categories
    ADD CONSTRAINT business_categories_pkey PRIMARY KEY (key);


--
-- Name: analyses ck_analyses_insights_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.analyses
    ADD CONSTRAINT ck_analyses_insights_jsonb CHECK (((insights IS NULL) OR (jsonb_typeof(insights) = 'object'::text))) NOT VALID;


--
-- Name: analyses ck_analyses_sources_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.analyses
    ADD CONSTRAINT ck_analyses_sources_jsonb CHECK (((sources IS NULL) OR (jsonb_typeof(sources) = 'object'::text))) NOT VALID;


--
-- Name: community_pool ck_pool_categories_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.community_pool
    ADD CONSTRAINT ck_pool_categories_jsonb CHECK (((categories IS NULL) OR (jsonb_typeof(categories) = ANY (ARRAY['array'::text, 'object'::text])))) NOT VALID;


--
-- Name: community_pool ck_pool_keywords_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.community_pool
    ADD CONSTRAINT ck_pool_keywords_jsonb CHECK (((description_keywords IS NULL) OR (jsonb_typeof(description_keywords) = ANY (ARRAY['array'::text, 'object'::text])))) NOT VALID;


--
-- Name: posts_hot ck_posts_hot_entities_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_hot
    ADD CONSTRAINT ck_posts_hot_entities_jsonb CHECK (((entities IS NULL) OR (jsonb_typeof(entities) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: posts_hot ck_posts_hot_labels_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_hot
    ADD CONSTRAINT ck_posts_hot_labels_jsonb CHECK (((content_labels IS NULL) OR (jsonb_typeof(content_labels) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: posts_hot ck_posts_hot_metadata_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_hot
    ADD CONSTRAINT ck_posts_hot_metadata_jsonb CHECK (((metadata IS NULL) OR (jsonb_typeof(metadata) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: posts_raw ck_posts_raw_metadata_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_raw
    ADD CONSTRAINT ck_posts_raw_metadata_jsonb CHECK (((metadata IS NULL) OR (jsonb_typeof(metadata) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: cleanup_logs cleanup_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cleanup_logs
    ADD CONSTRAINT cleanup_logs_pkey PRIMARY KEY (id);


--
-- Name: comment_scores comment_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comment_scores
    ADD CONSTRAINT comment_scores_pkey PRIMARY KEY (id);


--
-- Name: community_audit community_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_audit
    ADD CONSTRAINT community_audit_pkey PRIMARY KEY (id);


--
-- Name: community_category_map community_category_map_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_category_map
    ADD CONSTRAINT community_category_map_pkey PRIMARY KEY (community_id, category_key);


--
-- Name: community_import_history community_import_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_import_history
    ADD CONSTRAINT community_import_history_pkey PRIMARY KEY (id);


--
-- Name: community_roles_map community_roles_map_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_roles_map
    ADD CONSTRAINT community_roles_map_pkey PRIMARY KEY (subreddit);


--
-- Name: data_audit_events data_audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.data_audit_events
    ADD CONSTRAINT data_audit_events_pkey PRIMARY KEY (id);


--
-- Name: facts_quality_audit facts_quality_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facts_quality_audit
    ADD CONSTRAINT facts_quality_audit_pkey PRIMARY KEY (run_id);


--
-- Name: feedback_events feedback_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_events
    ADD CONSTRAINT feedback_events_pkey PRIMARY KEY (id);


--
-- Name: noise_labels noise_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.noise_labels
    ADD CONSTRAINT noise_labels_pkey PRIMARY KEY (id);


--
-- Name: authors pk_authors; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authors
    ADD CONSTRAINT pk_authors PRIMARY KEY (author_id);


--
-- Name: comments pk_comments; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT pk_comments PRIMARY KEY (id);


--
-- Name: community_cache pk_community_cache_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_cache
    ADD CONSTRAINT pk_community_cache_name PRIMARY KEY (community_name);


--
-- Name: community_pool pk_community_pool; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT pk_community_pool PRIMARY KEY (id);


--
-- Name: content_entities pk_content_entities; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_entities
    ADD CONSTRAINT pk_content_entities PRIMARY KEY (id);


--
-- Name: content_labels pk_content_labels; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_labels
    ADD CONSTRAINT pk_content_labels PRIMARY KEY (id);


--
-- Name: crawl_metrics pk_crawl_metrics; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_metrics
    ADD CONSTRAINT pk_crawl_metrics PRIMARY KEY (id);


--
-- Name: crawler_run_targets pk_crawler_run_targets; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_run_targets
    ADD CONSTRAINT pk_crawler_run_targets PRIMARY KEY (id);


--
-- Name: crawler_runs pk_crawler_runs; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_runs
    ADD CONSTRAINT pk_crawler_runs PRIMARY KEY (id);


--
-- Name: evidence_posts pk_evidence_posts; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence_posts
    ADD CONSTRAINT pk_evidence_posts PRIMARY KEY (id);


--
-- Name: evidences pk_evidences; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidences
    ADD CONSTRAINT pk_evidences PRIMARY KEY (id);


--
-- Name: facts_run_logs pk_facts_run_logs; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facts_run_logs
    ADD CONSTRAINT pk_facts_run_logs PRIMARY KEY (id);


--
-- Name: facts_snapshots pk_facts_snapshots; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facts_snapshots
    ADD CONSTRAINT pk_facts_snapshots PRIMARY KEY (id);


--
-- Name: insight_cards pk_insight_cards; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.insight_cards
    ADD CONSTRAINT pk_insight_cards PRIMARY KEY (id);


--
-- Name: maintenance_audit pk_maintenance_audit; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.maintenance_audit
    ADD CONSTRAINT pk_maintenance_audit PRIMARY KEY (id);


--
-- Name: discovered_communities pk_pending_communities; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT pk_pending_communities PRIMARY KEY (id);


--
-- Name: post_embeddings pk_post_embeddings; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_embeddings
    ADD CONSTRAINT pk_post_embeddings PRIMARY KEY (post_id, model_version);


--
-- Name: post_semantic_labels pk_post_semantic_labels; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_semantic_labels
    ADD CONSTRAINT pk_post_semantic_labels PRIMARY KEY (id);


--
-- Name: posts_archive pk_posts_archive; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_archive
    ADD CONSTRAINT pk_posts_archive PRIMARY KEY (id);


--
-- Name: posts_raw pk_posts_raw; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw
    ADD CONSTRAINT pk_posts_raw PRIMARY KEY (id);


--
-- Name: quality_metrics pk_quality_metrics; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quality_metrics
    ADD CONSTRAINT pk_quality_metrics PRIMARY KEY (id);


--
-- Name: semantic_audit_logs pk_semantic_audit_logs; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_audit_logs
    ADD CONSTRAINT pk_semantic_audit_logs PRIMARY KEY (id);


--
-- Name: semantic_candidates pk_semantic_candidates; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_candidates
    ADD CONSTRAINT pk_semantic_candidates PRIMARY KEY (id);


--
-- Name: semantic_concepts pk_semantic_concepts; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_concepts
    ADD CONSTRAINT pk_semantic_concepts PRIMARY KEY (id);


--
-- Name: semantic_rules pk_semantic_rules; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_rules
    ADD CONSTRAINT pk_semantic_rules PRIMARY KEY (id);


--
-- Name: semantic_terms pk_semantic_terms; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_terms
    ADD CONSTRAINT pk_semantic_terms PRIMARY KEY (id);


--
-- Name: storage_metrics pk_storage_metrics; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.storage_metrics
    ADD CONSTRAINT pk_storage_metrics PRIMARY KEY (id);


--
-- Name: subreddit_snapshots pk_subreddit_snapshots; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subreddit_snapshots
    ADD CONSTRAINT pk_subreddit_snapshots PRIMARY KEY (id);


--
-- Name: tier_audit_logs pk_tier_audit_logs; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tier_audit_logs
    ADD CONSTRAINT pk_tier_audit_logs PRIMARY KEY (id);


--
-- Name: tier_suggestions pk_tier_suggestions; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tier_suggestions
    ADD CONSTRAINT pk_tier_suggestions PRIMARY KEY (id);


--
-- Name: post_scores post_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_scores
    ADD CONSTRAINT post_scores_pkey PRIMARY KEY (id);


--
-- Name: posts_hot posts_hot_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_hot
    ADD CONSTRAINT posts_hot_pkey PRIMARY KEY (id);


--
-- Name: posts_quarantine posts_quarantine_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_quarantine
    ADD CONSTRAINT posts_quarantine_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: analyses uq_analyses_task_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT uq_analyses_task_id UNIQUE (task_id, analysis_version);


--
-- Name: comments uq_comments_reddit_comment_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT uq_comments_reddit_comment_id UNIQUE (reddit_comment_id);


--
-- Name: community_pool uq_community_pool_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT uq_community_pool_name UNIQUE (name);


--
-- Name: crawl_metrics uq_crawl_metrics_date_hour; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_metrics
    ADD CONSTRAINT uq_crawl_metrics_date_hour UNIQUE (metric_date, metric_hour);


--
-- Name: evidence_posts uq_evidence_posts_probe_query_post; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence_posts
    ADD CONSTRAINT uq_evidence_posts_probe_query_post UNIQUE (probe_source, source_query_hash, source_post_id);


--
-- Name: insight_cards uq_insight_cards_task_title; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.insight_cards
    ADD CONSTRAINT uq_insight_cards_task_title UNIQUE (task_id, title);


--
-- Name: discovered_communities uq_pending_communities_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT uq_pending_communities_name UNIQUE (name);


--
-- Name: post_semantic_labels uq_post_semantic_labels_post_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_semantic_labels
    ADD CONSTRAINT uq_post_semantic_labels_post_id UNIQUE (post_id);


--
-- Name: posts_raw uq_posts_raw_source_version; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw
    ADD CONSTRAINT uq_posts_raw_source_version UNIQUE (source, source_post_id, version);


--
-- Name: semantic_candidates uq_semantic_candidates_term; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_candidates
    ADD CONSTRAINT uq_semantic_candidates_term UNIQUE (term);


--
-- Name: semantic_concepts uq_semantic_concepts_code; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_concepts
    ADD CONSTRAINT uq_semantic_concepts_code UNIQUE (code);


--
-- Name: semantic_rules uq_semantic_rules_term_type; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_rules
    ADD CONSTRAINT uq_semantic_rules_term_type UNIQUE (concept_id, term, rule_type);


--
-- Name: semantic_terms uq_semantic_terms_canonical; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_terms
    ADD CONSTRAINT uq_semantic_terms_canonical UNIQUE (canonical);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vertical_map vertical_map_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vertical_map
    ADD CONSTRAINT vertical_map_pkey PRIMARY KEY (subreddit);


--
-- Name: idx_analyses_task_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analyses_task_created ON public.analyses USING btree (task_id, created_at) WHERE (task_id IS NOT NULL);


--
-- Name: idx_beta_feedback_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_beta_feedback_created_at ON public.beta_feedback USING btree (created_at);


--
-- Name: idx_beta_feedback_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_beta_feedback_task_id ON public.beta_feedback USING btree (task_id);


--
-- Name: idx_beta_feedback_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_beta_feedback_user_id ON public.beta_feedback USING btree (user_id);


--
-- Name: idx_cleanup_logs_time_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cleanup_logs_time_success ON public.cleanup_logs USING btree (executed_at DESC, success, total_records_cleaned);


--
-- Name: idx_comment_scores_comment_latest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comment_scores_comment_latest ON public.comment_scores USING btree (comment_id) WHERE (is_latest = true);


--
-- Name: idx_comment_scores_pool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comment_scores_pool ON public.comment_scores USING btree (business_pool) WHERE (is_latest = true);


--
-- Name: idx_comment_scores_rule_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comment_scores_rule_version ON public.comment_scores USING btree (rule_version);


--
-- Name: idx_comments_business_pool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_business_pool ON public.comments USING btree (business_pool);


--
-- Name: idx_comments_captured_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_captured_at ON public.comments USING btree (captured_at);


--
-- Name: idx_comments_community_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_community_run_id ON public.comments USING btree (community_run_id) WHERE (community_run_id IS NOT NULL);


--
-- Name: idx_comments_crawl_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_crawl_run_id ON public.comments USING btree (crawl_run_id) WHERE (crawl_run_id IS NOT NULL);


--
-- Name: idx_comments_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_expires_at ON public.comments USING btree (expires_at);


--
-- Name: idx_comments_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_parent_id ON public.comments USING btree (parent_id);


--
-- Name: idx_comments_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_post_id ON public.comments USING btree (post_id);


--
-- Name: idx_comments_post_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_post_time ON public.comments USING btree (source, source_post_id, created_utc);


--
-- Name: idx_comments_subreddit_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_subreddit_created ON public.comments USING btree (subreddit, created_utc DESC);


--
-- Name: idx_comments_subreddit_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_subreddit_time ON public.comments USING btree (subreddit, created_utc);


--
-- Name: idx_community_audit_comm_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_audit_comm_time ON public.community_audit USING btree (community_id, created_at DESC);


--
-- Name: idx_community_import_history_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_import_history_created ON public.community_import_history USING btree (created_at);


--
-- Name: idx_community_import_history_uploaded_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_import_history_uploaded_by ON public.community_import_history USING btree (uploaded_by_user_id);


--
-- Name: idx_community_pool_categories_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_categories_gin ON public.community_pool USING gin (categories);


--
-- Name: idx_community_pool_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_deleted_at ON public.community_pool USING btree (deleted_at);


--
-- Name: idx_community_pool_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_is_active ON public.community_pool USING btree (is_active);


--
-- Name: idx_community_pool_name_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_name_key ON public.community_pool USING btree (name_key);


--
-- Name: idx_community_pool_tier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_tier ON public.community_pool USING btree (tier);


--
-- Name: idx_content_entities_entity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_entities_entity ON public.content_entities USING btree (entity, entity_type);


--
-- Name: idx_content_entities_target; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_entities_target ON public.content_entities USING btree (content_type, content_id);


--
-- Name: idx_content_labels_cat_aspect; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_labels_cat_aspect ON public.content_labels USING btree (category, aspect);


--
-- Name: idx_content_labels_sentiment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_labels_sentiment ON public.content_labels USING btree (sentiment_score);


--
-- Name: idx_content_labels_target; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_labels_target ON public.content_labels USING btree (content_type, content_id);


--
-- Name: idx_crawl_metrics_crawl_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawl_metrics_crawl_run_id ON public.crawl_metrics USING btree (crawl_run_id) WHERE (crawl_run_id IS NOT NULL);


--
-- Name: idx_crawler_run_targets_crawl_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_run_targets_crawl_run_id ON public.crawler_run_targets USING btree (crawl_run_id);


--
-- Name: idx_crawler_run_targets_plan_kind; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_run_targets_plan_kind ON public.crawler_run_targets USING btree (plan_kind) WHERE (plan_kind IS NOT NULL);


--
-- Name: idx_crawler_run_targets_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_run_targets_started_at ON public.crawler_run_targets USING btree (started_at);


--
-- Name: idx_crawler_run_targets_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_run_targets_status ON public.crawler_run_targets USING btree (status);


--
-- Name: idx_crawler_run_targets_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_run_targets_subreddit ON public.crawler_run_targets USING btree (subreddit);


--
-- Name: idx_crawler_runs_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_runs_started_at ON public.crawler_runs USING btree (started_at);


--
-- Name: idx_crawler_runs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawler_runs_status ON public.crawler_runs USING btree (status);


--
-- Name: idx_data_audit_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_audit_created ON public.data_audit_events USING btree (created_at DESC);


--
-- Name: idx_data_audit_event; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_audit_event ON public.data_audit_events USING btree (event_type);


--
-- Name: idx_data_audit_target; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_audit_target ON public.data_audit_events USING btree (target_type, target_id);


--
-- Name: idx_discovered_communities_cooldown; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovered_communities_cooldown ON public.discovered_communities USING btree (cooldown_until) WHERE (cooldown_until IS NOT NULL);


--
-- Name: idx_discovered_communities_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovered_communities_deleted_at ON public.discovered_communities USING btree (deleted_at);


--
-- Name: idx_discovered_communities_discovered_count; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovered_communities_discovered_count ON public.discovered_communities USING btree (discovered_count);


--
-- Name: idx_discovered_communities_reviewed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovered_communities_reviewed_by ON public.discovered_communities USING btree (reviewed_by);


--
-- Name: idx_discovered_communities_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovered_communities_status ON public.discovered_communities USING btree (status);


--
-- Name: idx_discovered_communities_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovered_communities_task_id ON public.discovered_communities USING btree (discovered_from_task_id);


--
-- Name: idx_evidence_posts_crawl_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidence_posts_crawl_run_id ON public.evidence_posts USING btree (crawl_run_id);


--
-- Name: idx_evidence_posts_probe_query; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidence_posts_probe_query ON public.evidence_posts USING btree (probe_source, source_query_hash);


--
-- Name: idx_evidence_posts_subreddit_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidence_posts_subreddit_created ON public.evidence_posts USING btree (subreddit, created_at);


--
-- Name: idx_evidence_posts_target_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidence_posts_target_id ON public.evidence_posts USING btree (target_id);


--
-- Name: idx_evidences_insight_card_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidences_insight_card_id ON public.evidences USING btree (insight_card_id);


--
-- Name: idx_evidences_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidences_score ON public.evidences USING btree (score);


--
-- Name: idx_evidences_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidences_subreddit ON public.evidences USING btree (subreddit);


--
-- Name: idx_evidences_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidences_timestamp ON public.evidences USING btree ("timestamp");


--
-- Name: idx_facts_quality_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_quality_created_at ON public.facts_quality_audit USING btree (created_at DESC);


--
-- Name: idx_facts_run_logs_audit_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_run_logs_audit_level ON public.facts_run_logs USING btree (audit_level);


--
-- Name: idx_facts_run_logs_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_run_logs_created_at ON public.facts_run_logs USING btree (created_at);


--
-- Name: idx_facts_run_logs_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_run_logs_expires_at ON public.facts_run_logs USING btree (expires_at);


--
-- Name: idx_facts_run_logs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_run_logs_status ON public.facts_run_logs USING btree (status);


--
-- Name: idx_facts_run_logs_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_run_logs_task_id ON public.facts_run_logs USING btree (task_id);


--
-- Name: idx_facts_snapshots_audit_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_audit_level ON public.facts_snapshots USING btree (audit_level);


--
-- Name: idx_facts_snapshots_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_created_at ON public.facts_snapshots USING btree (created_at);


--
-- Name: idx_facts_snapshots_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_expires_at ON public.facts_snapshots USING btree (expires_at);


--
-- Name: idx_facts_snapshots_passed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_passed ON public.facts_snapshots USING btree (passed);


--
-- Name: idx_facts_snapshots_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_status ON public.facts_snapshots USING btree (status);


--
-- Name: idx_facts_snapshots_task_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_task_created ON public.facts_snapshots USING btree (task_id, created_at);


--
-- Name: idx_facts_snapshots_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_task_id ON public.facts_snapshots USING btree (task_id);


--
-- Name: idx_facts_snapshots_tier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_snapshots_tier ON public.facts_snapshots USING btree (tier);


--
-- Name: idx_insight_cards_confidence; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_insight_cards_confidence ON public.insight_cards USING btree (confidence);


--
-- Name: idx_insight_cards_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_insight_cards_created_at ON public.insight_cards USING btree (created_at);


--
-- Name: idx_insight_cards_subreddits_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_insight_cards_subreddits_gin ON public.insight_cards USING gin (subreddits);


--
-- Name: idx_insight_cards_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_insight_cards_task_id ON public.insight_cards USING btree (task_id);


--
-- Name: idx_maintenance_audit_started; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_maintenance_audit_started ON public.maintenance_audit USING btree (started_at);


--
-- Name: idx_maintenance_audit_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_maintenance_audit_task ON public.maintenance_audit USING btree (task_name);


--
-- Name: idx_metrics_metric_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_metrics_metric_date ON public.crawl_metrics USING btree (metric_date);


--
-- Name: idx_metrics_metric_hour; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_metrics_metric_hour ON public.crawl_metrics USING btree (metric_hour);


--
-- Name: idx_mv_entities_name_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mv_entities_name_type ON public.mv_analysis_entities USING btree (entity_name, entity_type);


--
-- Name: idx_mv_entities_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mv_entities_post_id ON public.mv_analysis_entities USING btree (post_id);


--
-- Name: idx_mv_labels_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mv_labels_post_id ON public.mv_analysis_labels USING btree (post_id);


--
-- Name: idx_mv_monthly_trend_month; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mv_monthly_trend_month ON public.mv_monthly_trend USING btree (month_start);


--
-- Name: idx_noise_labels_target; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_noise_labels_target ON public.noise_labels USING btree (noise_type, content_type, content_id);


--
-- Name: idx_post_comment_stats_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_post_comment_stats_post_id ON public.post_comment_stats USING btree (post_id);


--
-- Name: idx_post_embeddings_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_embeddings_hnsw ON public.post_embeddings USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='128');


--
-- Name: idx_post_embeddings_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_embeddings_post_id ON public.post_embeddings USING btree (post_id);


--
-- Name: idx_post_scores_pool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_scores_pool ON public.post_scores USING btree (business_pool) WHERE (is_latest = true);


--
-- Name: idx_post_scores_post_id_full; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_scores_post_id_full ON public.post_scores USING btree (post_id);


--
-- Name: idx_post_scores_post_latest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_scores_post_latest ON public.post_scores USING btree (post_id) WHERE (is_latest = true);


--
-- Name: idx_post_scores_rule_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_scores_rule_version ON public.post_scores USING btree (rule_version);


--
-- Name: idx_post_semantic_labels_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_post_semantic_labels_post_id ON public.post_semantic_labels USING btree (post_id);


--
-- Name: idx_posts_archive_source_post; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_archive_source_post ON public.posts_archive USING btree (source, source_post_id);


--
-- Name: idx_posts_fulltext; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_fulltext ON public.posts_raw USING gin (to_tsvector('english'::regconfig, ((COALESCE(title, ''::text) || ' '::text) || COALESCE(body, ''::text))));


--
-- Name: idx_posts_hot_content_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_content_gin ON public.posts_hot USING gin (content_tsvector);


--
-- Name: idx_posts_hot_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_created_at ON public.posts_hot USING btree (created_at DESC);


--
-- Name: idx_posts_hot_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_expires_at ON public.posts_hot USING btree (expires_at);


--
-- Name: idx_posts_hot_metadata_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_metadata_gin ON public.posts_hot USING gin (metadata);


--
-- Name: idx_posts_hot_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_subreddit ON public.posts_hot USING btree (subreddit, created_at DESC);


--
-- Name: idx_posts_hot_subreddit_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_subreddit_expires ON public.posts_hot USING btree (subreddit, expires_at);


--
-- Name: idx_posts_latest_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_latest_created_at ON public.posts_latest USING btree (created_at DESC);


--
-- Name: idx_posts_latest_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_latest_subreddit ON public.posts_latest USING btree (subreddit, created_at DESC);


--
-- Name: idx_posts_latest_text_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_latest_text_hash ON public.posts_latest USING btree (text_norm_hash);


--
-- Name: idx_posts_latest_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_posts_latest_unique ON public.posts_latest USING btree (source, source_post_id);


--
-- Name: idx_posts_latest_value_pool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_latest_value_pool ON public.posts_latest USING btree (business_pool, value_score DESC);


--
-- Name: idx_posts_raw_business_pool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_business_pool ON public.posts_raw USING btree (business_pool);


--
-- Name: idx_posts_raw_community_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_community_id ON public.posts_raw USING btree (community_id);


--
-- Name: idx_posts_raw_community_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_community_run_id ON public.posts_raw USING btree (community_run_id) WHERE (community_run_id IS NOT NULL);


--
-- Name: idx_posts_raw_crawl_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_crawl_run_id ON public.posts_raw USING btree (crawl_run_id) WHERE (crawl_run_id IS NOT NULL);


--
-- Name: idx_posts_raw_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_created_at ON public.posts_raw USING btree (created_at DESC);


--
-- Name: idx_posts_raw_current; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_current ON public.posts_raw USING btree (source, source_post_id, is_current) WHERE (is_current = true);


--
-- Name: idx_posts_raw_duplicate_flag; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_duplicate_flag ON public.posts_raw USING btree (is_duplicate);


--
-- Name: idx_posts_raw_fetched_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_fetched_at ON public.posts_raw USING btree (fetched_at DESC);


--
-- Name: idx_posts_raw_source_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_source_post_id ON public.posts_raw USING btree (source, source_post_id);


--
-- Name: idx_posts_raw_source_track; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_source_track ON public.posts_raw USING btree (source_track);


--
-- Name: idx_posts_raw_spam_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_spam_category ON public.posts_raw USING btree (spam_category);


--
-- Name: idx_posts_raw_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_subreddit ON public.posts_raw USING btree (subreddit, created_at DESC);


--
-- Name: idx_posts_raw_text_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_text_hash ON public.posts_raw USING btree (text_norm_hash);


--
-- Name: idx_posts_raw_value_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_value_score ON public.posts_raw USING btree (value_score DESC);


--
-- Name: idx_psl_l1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_psl_l1 ON public.post_semantic_labels USING btree (l1_category);


--
-- Name: idx_psl_l1_sec; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_psl_l1_sec ON public.post_semantic_labels USING btree (l1_secondary);


--
-- Name: idx_psl_l2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_psl_l2 ON public.post_semantic_labels USING btree (l2_business);


--
-- Name: idx_psl_sentiment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_psl_sentiment ON public.post_semantic_labels USING btree (sentiment_score);


--
-- Name: idx_psl_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_psl_tags ON public.post_semantic_labels USING gin (tags);


--
-- Name: idx_quality_metrics_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_quality_metrics_date ON public.quality_metrics USING btree (date);


--
-- Name: idx_reports_template; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reports_template ON public.reports USING btree (template_version);


--
-- Name: idx_semantic_audit_logs_changes_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_audit_logs_changes_gin ON public.semantic_audit_logs USING gin (changes);


--
-- Name: idx_semantic_rules_active_concept; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_rules_active_concept ON public.semantic_rules USING btree (concept_id) WHERE (is_active = true);


--
-- Name: idx_semantic_rules_concept; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_rules_concept ON public.semantic_rules USING btree (concept_id);


--
-- Name: idx_semantic_rules_term; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_rules_term ON public.semantic_rules USING btree (term);


--
-- Name: idx_storage_metrics_collected_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_storage_metrics_collected_at ON public.storage_metrics USING btree (collected_at);


--
-- Name: idx_subreddit_snapshots_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subreddit_snapshots_subreddit ON public.subreddit_snapshots USING btree (subreddit);


--
-- Name: idx_subreddit_snapshots_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subreddit_snapshots_time ON public.subreddit_snapshots USING btree (subreddit, captured_at);


--
-- Name: idx_tasks_completed_cleanup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_completed_cleanup ON public.tasks USING btree (status, completed_at) WHERE (((status)::text = 'completed'::text) AND (completed_at IS NOT NULL));


--
-- Name: idx_tasks_failed_cleanup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_failed_cleanup ON public.tasks USING btree (status, updated_at) WHERE (((status)::text = 'failed'::text) AND (updated_at IS NOT NULL));


--
-- Name: idx_users_active_login; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_active_login ON public.users USING btree (is_active, created_at) WHERE (is_active = true);


--
-- Name: ix_analyses_confidence_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_confidence_created ON public.analyses USING btree (confidence_score DESC, created_at DESC);


--
-- Name: ix_analyses_confidence_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_confidence_desc ON public.analyses USING btree (confidence_score DESC);


--
-- Name: ix_analyses_created_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_created_desc ON public.analyses USING btree (created_at DESC);


--
-- Name: ix_analyses_insights_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_insights_gin ON public.analyses USING gin (insights jsonb_path_ops);


--
-- Name: ix_analyses_sources_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_sources_gin ON public.analyses USING gin (sources);


--
-- Name: ix_analyses_task_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_task_created ON public.analyses USING btree (task_id, created_at DESC);


--
-- Name: ix_analyses_version_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_analyses_version_created ON public.analyses USING btree (analysis_version, created_at DESC);


--
-- Name: ix_cleanup_logs_executed_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cleanup_logs_executed_desc ON public.cleanup_logs USING btree (executed_at DESC);


--
-- Name: ix_cleanup_logs_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cleanup_logs_success ON public.cleanup_logs USING btree (success);


--
-- Name: ix_feedback_events_task; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_feedback_events_task ON public.feedback_events USING btree (task_id);


--
-- Name: ix_feedback_events_type_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_feedback_events_type_time ON public.feedback_events USING btree (event_type, created_at);


--
-- Name: ix_reports_analysis_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reports_analysis_active ON public.reports USING btree (analysis_id) WHERE ((status)::text = 'active'::text);


--
-- Name: ix_reports_created_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reports_created_desc ON public.reports USING btree (created_at DESC);


--
-- Name: ix_semantic_audit_logs_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_audit_logs_created_at ON public.semantic_audit_logs USING btree (created_at);


--
-- Name: ix_semantic_audit_logs_entity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_audit_logs_entity ON public.semantic_audit_logs USING btree (entity_type, entity_id);


--
-- Name: ix_semantic_audit_logs_operator_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_audit_logs_operator_id ON public.semantic_audit_logs USING btree (operator_id);


--
-- Name: ix_semantic_candidates_first_seen_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_candidates_first_seen_at ON public.semantic_candidates USING btree (first_seen_at);


--
-- Name: ix_semantic_candidates_frequency; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_candidates_frequency ON public.semantic_candidates USING btree (frequency);


--
-- Name: ix_semantic_candidates_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_candidates_status ON public.semantic_candidates USING btree (status);


--
-- Name: ix_semantic_rules_domain; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_rules_domain ON public.semantic_rules USING btree (domain);


--
-- Name: ix_semantic_terms_canonical; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_semantic_terms_canonical ON public.semantic_terms USING btree (canonical);


--
-- Name: ix_semantic_terms_category_layer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_terms_category_layer ON public.semantic_terms USING btree (category, layer);


--
-- Name: ix_semantic_terms_lifecycle; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_semantic_terms_lifecycle ON public.semantic_terms USING btree (lifecycle);


--
-- Name: ix_tasks_audit_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_audit_level ON public.tasks USING btree (audit_level);


--
-- Name: ix_tasks_processing; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_processing ON public.tasks USING btree (status, created_at) WHERE ((status)::text = 'processing'::text);


--
-- Name: ix_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_status ON public.tasks USING btree (status) WHERE ((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('processing'::character varying)::text]));


--
-- Name: ix_tasks_status_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_status_created ON public.tasks USING btree (status, created_at DESC);


--
-- Name: ix_tasks_topic_profile_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_topic_profile_id ON public.tasks USING btree (topic_profile_id);


--
-- Name: ix_tasks_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_user_created ON public.tasks USING btree (user_id, created_at DESC);


--
-- Name: ix_tasks_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tasks_user_status ON public.tasks USING btree (user_id, status);


--
-- Name: ix_tier_audit_logs_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tier_audit_logs_action ON public.tier_audit_logs USING btree (action);


--
-- Name: ix_tier_audit_logs_community_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tier_audit_logs_community_name ON public.tier_audit_logs USING btree (community_name);


--
-- Name: ix_tier_audit_logs_is_rolled_back; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tier_audit_logs_is_rolled_back ON public.tier_audit_logs USING btree (is_rolled_back);


--
-- Name: ix_tier_suggestions_community_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tier_suggestions_community_name ON public.tier_suggestions USING btree (community_name);


--
-- Name: ix_tier_suggestions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tier_suggestions_status ON public.tier_suggestions USING btree (status);


--
-- Name: ix_users_email_lookup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_email_lookup ON public.users USING btree (email) WHERE (is_active = true);


--
-- Name: ix_users_tenant_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_tenant_active ON public.users USING btree (tenant_id, is_active) WHERE (is_active = true);


--
-- Name: ix_users_tenant_email_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_tenant_email_unique ON public.users USING btree (tenant_id, email) WHERE (is_active = true);


--
-- Name: ix_users_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id);


--
-- Name: uq_crawler_run_targets_run_idempotency_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_crawler_run_targets_run_idempotency_key ON public.crawler_run_targets USING btree (crawl_run_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);


--
-- Name: uq_posts_hot_source_post; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_posts_hot_source_post ON public.posts_hot USING btree (source, source_post_id);


--
-- Name: ux_comment_scores_latest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ux_comment_scores_latest ON public.comment_scores USING btree (comment_id) WHERE (is_latest = true);


--
-- Name: ux_post_scores_latest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ux_post_scores_latest ON public.post_scores USING btree (post_id) WHERE (is_latest = true);


--
-- Name: posts_raw enforce_scd2_posts_raw; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER enforce_scd2_posts_raw BEFORE INSERT OR UPDATE ON public.posts_raw FOR EACH ROW EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2();


--
-- Name: analyses tr_analyses_completion; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER tr_analyses_completion AFTER INSERT ON public.analyses FOR EACH ROW EXECUTE FUNCTION public.update_task_completion_status();


--
-- Name: tasks tr_tasks_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER tr_tasks_updated_at BEFORE UPDATE ON public.tasks FOR EACH ROW EXECUTE FUNCTION public.update_tasks_updated_at();


--
-- Name: comments trg_adjust_ttl_on_score; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_adjust_ttl_on_score BEFORE UPDATE OF value_score ON public.comments FOR EACH ROW EXECUTE FUNCTION public.adjust_comment_ttl_on_score();


--
-- Name: posts_raw trg_auto_score_posts; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_auto_score_posts BEFORE INSERT ON public.posts_raw FOR EACH ROW EXECUTE FUNCTION public.trg_func_auto_score_posts();


--
-- Name: comments trg_clean_comments_on_insert; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_clean_comments_on_insert BEFORE INSERT ON public.comments FOR EACH ROW EXECUTE FUNCTION public.trg_func_auto_clean_comments();


--
-- Name: posts_raw trg_fill_normalized_fields; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_fill_normalized_fields BEFORE INSERT OR UPDATE ON public.posts_raw FOR EACH ROW EXECUTE FUNCTION public.fill_normalized_fields();


--
-- Name: comments trg_set_comment_expires; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_set_comment_expires BEFORE INSERT ON public.comments FOR EACH ROW EXECUTE FUNCTION public.set_comment_expires_at();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: beta_feedback beta_feedback_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.beta_feedback
    ADD CONSTRAINT beta_feedback_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: beta_feedback beta_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.beta_feedback
    ADD CONSTRAINT beta_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: comment_scores comment_scores_comment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comment_scores
    ADD CONSTRAINT comment_scores_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id) ON DELETE CASCADE;


--
-- Name: community_audit community_audit_community_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_audit
    ADD CONSTRAINT community_audit_community_id_fkey FOREIGN KEY (community_id) REFERENCES public.community_pool(id);


--
-- Name: analyses fk_analyses_task_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyses
    ADD CONSTRAINT fk_analyses_task_id FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: comments fk_comments_posts_raw; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT fk_comments_posts_raw FOREIGN KEY (post_id) REFERENCES public.posts_raw(id) ON DELETE CASCADE;


--
-- Name: community_import_history fk_community_import_history_created_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_import_history
    ADD CONSTRAINT fk_community_import_history_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_import_history fk_community_import_history_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_import_history
    ADD CONSTRAINT fk_community_import_history_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_import_history fk_community_import_history_uploaded_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_import_history
    ADD CONSTRAINT fk_community_import_history_uploaded_by_user_id FOREIGN KEY (uploaded_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_pool fk_community_pool_created_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT fk_community_pool_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_pool fk_community_pool_deleted_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT fk_community_pool_deleted_by FOREIGN KEY (deleted_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_pool fk_community_pool_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT fk_community_pool_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: crawler_run_targets fk_crawler_run_targets_crawl_run_id_crawler_runs; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_run_targets
    ADD CONSTRAINT fk_crawler_run_targets_crawl_run_id_crawler_runs FOREIGN KEY (crawl_run_id) REFERENCES public.crawler_runs(id) ON DELETE CASCADE;


--
-- Name: discovered_communities fk_discovered_communities_created_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_discovered_communities_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: discovered_communities fk_discovered_communities_deleted_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_discovered_communities_deleted_by FOREIGN KEY (deleted_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: discovered_communities fk_discovered_communities_discovered_from_task_id_tasks; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_discovered_communities_discovered_from_task_id_tasks FOREIGN KEY (discovered_from_task_id) REFERENCES public.tasks(id) ON DELETE SET NULL;


--
-- Name: discovered_communities fk_discovered_communities_reviewed_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_discovered_communities_reviewed_by FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: discovered_communities fk_discovered_communities_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_discovered_communities_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: discovered_communities fk_discovered_to_pool; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_discovered_to_pool FOREIGN KEY (name) REFERENCES public.community_pool(name) ON DELETE SET NULL;


--
-- Name: post_embeddings fk_embeddings_post; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_embeddings
    ADD CONSTRAINT fk_embeddings_post FOREIGN KEY (post_id) REFERENCES public.posts_raw(id) ON DELETE CASCADE;


--
-- Name: evidence_posts fk_evidence_posts_crawl_run_id_crawler_runs; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence_posts
    ADD CONSTRAINT fk_evidence_posts_crawl_run_id_crawler_runs FOREIGN KEY (crawl_run_id) REFERENCES public.crawler_runs(id) ON DELETE SET NULL;


--
-- Name: evidence_posts fk_evidence_posts_target_id_crawler_run_targets; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence_posts
    ADD CONSTRAINT fk_evidence_posts_target_id_crawler_run_targets FOREIGN KEY (target_id) REFERENCES public.crawler_run_targets(id) ON DELETE SET NULL;


--
-- Name: evidences fk_evidences_insight_card_id_insight_cards; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidences
    ADD CONSTRAINT fk_evidences_insight_card_id_insight_cards FOREIGN KEY (insight_card_id) REFERENCES public.insight_cards(id) ON DELETE CASCADE;


--
-- Name: facts_run_logs fk_facts_run_logs_task_id_tasks; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facts_run_logs
    ADD CONSTRAINT fk_facts_run_logs_task_id_tasks FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: facts_snapshots fk_facts_snapshots_task_id_tasks; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facts_snapshots
    ADD CONSTRAINT fk_facts_snapshots_task_id_tasks FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: insight_cards fk_insight_cards_task_id_tasks; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.insight_cards
    ADD CONSTRAINT fk_insight_cards_task_id_tasks FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: community_category_map fk_map_category; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_category_map
    ADD CONSTRAINT fk_map_category FOREIGN KEY (category_key) REFERENCES public.business_categories(key) ON DELETE CASCADE;


--
-- Name: community_category_map fk_map_community; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_category_map
    ADD CONSTRAINT fk_map_community FOREIGN KEY (community_id) REFERENCES public.community_pool(id) ON DELETE CASCADE;


--
-- Name: discovered_communities fk_pending_communities_task_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_communities
    ADD CONSTRAINT fk_pending_communities_task_id FOREIGN KEY (discovered_from_task_id) REFERENCES public.tasks(id) ON DELETE SET NULL;


--
-- Name: post_semantic_labels fk_post_semantic_labels_post; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_semantic_labels
    ADD CONSTRAINT fk_post_semantic_labels_post FOREIGN KEY (post_id) REFERENCES public.posts_raw(id) ON DELETE RESTRICT;


--
-- Name: posts_raw fk_posts_raw_author; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw
    ADD CONSTRAINT fk_posts_raw_author FOREIGN KEY (author_id) REFERENCES public.authors(author_id) ON DELETE SET NULL;


--
-- Name: posts_raw fk_posts_raw_duplicate_of; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw
    ADD CONSTRAINT fk_posts_raw_duplicate_of FOREIGN KEY (duplicate_of_id) REFERENCES public.posts_raw(id) ON DELETE RESTRICT;


--
-- Name: semantic_audit_logs fk_semantic_audit_logs_operator_id_users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_audit_logs
    ADD CONSTRAINT fk_semantic_audit_logs_operator_id_users FOREIGN KEY (operator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semantic_candidates fk_semantic_candidates_created_by_users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_candidates
    ADD CONSTRAINT fk_semantic_candidates_created_by_users FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semantic_candidates fk_semantic_candidates_reviewed_by_users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_candidates
    ADD CONSTRAINT fk_semantic_candidates_reviewed_by_users FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semantic_candidates fk_semantic_candidates_updated_by_users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_candidates
    ADD CONSTRAINT fk_semantic_candidates_updated_by_users FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: semantic_rules fk_semantic_rules_concept_id_semantic_concepts; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_rules
    ADD CONSTRAINT fk_semantic_rules_concept_id_semantic_concepts FOREIGN KEY (concept_id) REFERENCES public.semantic_concepts(id) ON DELETE CASCADE;


--
-- Name: post_scores post_scores_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_scores
    ADD CONSTRAINT post_scores_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts_raw(id) ON DELETE CASCADE;


--
-- Name: reports reports_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.analyses(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: analyses; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

--
-- Name: analyses policy_analyses_tenant_isolation; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY policy_analyses_tenant_isolation ON public.analyses USING ((task_id IN ( SELECT tasks.id
   FROM public.tasks
  WHERE (tasks.user_id = (current_setting('app.current_user_id'::text))::uuid))));


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: hujia
--

GRANT USAGE ON SCHEMA public TO app_user;


--
-- Name: FUNCTION safe_delete_community(community_name_param text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.safe_delete_community(community_name_param text) TO app_user;


--
-- Name: TABLE alembic_version; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.alembic_version TO app_user;


--
-- Name: TABLE analyses; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.analyses TO app_user;


--
-- Name: TABLE analytics_community_history; Type: ACL; Schema: public; Owner: hujia
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.analytics_community_history TO app_user;


--
-- Name: TABLE authors; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.authors TO app_user;


--
-- Name: TABLE beta_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.beta_feedback TO app_user;


--
-- Name: TABLE business_categories; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.business_categories TO app_user;


--
-- Name: TABLE cleanup_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.cleanup_logs TO app_user;


--
-- Name: TABLE cleanup_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.cleanup_stats TO app_user;


--
-- Name: TABLE comments; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.comments TO app_user;


--
-- Name: SEQUENCE comments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.comments_id_seq TO app_user;


--
-- Name: TABLE community_cache; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.community_cache TO app_user;


--
-- Name: TABLE community_category_map; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.community_category_map TO app_user;


--
-- Name: TABLE community_import_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.community_import_history TO app_user;


--
-- Name: SEQUENCE community_import_history_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.community_import_history_id_seq TO app_user;


--
-- Name: TABLE community_pool; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.community_pool TO app_user;


--
-- Name: SEQUENCE community_pool_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.community_pool_id_seq TO app_user;


--
-- Name: TABLE content_entities; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.content_entities TO app_user;


--
-- Name: SEQUENCE content_entities_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.content_entities_id_seq TO app_user;


--
-- Name: TABLE content_labels; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.content_labels TO app_user;


--
-- Name: SEQUENCE content_labels_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.content_labels_id_seq TO app_user;


--
-- Name: TABLE crawl_metrics; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.crawl_metrics TO app_user;


--
-- Name: SEQUENCE crawl_metrics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.crawl_metrics_id_seq TO app_user;


--
-- Name: TABLE discovered_communities; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.discovered_communities TO app_user;


--
-- Name: SEQUENCE discovered_communities_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.discovered_communities_id_seq TO app_user;


--
-- Name: TABLE evidences; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.evidences TO app_user;


--
-- Name: TABLE feedback_events; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.feedback_events TO app_user;


--
-- Name: TABLE insight_cards; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.insight_cards TO app_user;


--
-- Name: TABLE maintenance_audit; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.maintenance_audit TO app_user;


--
-- Name: SEQUENCE maintenance_audit_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.maintenance_audit_id_seq TO app_user;


--
-- Name: TABLE posts_raw; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.posts_raw TO app_user;


--
-- Name: TABLE post_embeddings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.post_embeddings TO app_user;


--
-- Name: TABLE post_semantic_labels; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.post_semantic_labels TO app_user;


--
-- Name: SEQUENCE post_semantic_labels_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.post_semantic_labels_id_seq TO app_user;


--
-- Name: TABLE posts_archive; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.posts_archive TO app_user;


--
-- Name: SEQUENCE posts_archive_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.posts_archive_id_seq TO app_user;


--
-- Name: SEQUENCE posts_hot_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.posts_hot_id_seq TO app_user;


--
-- Name: TABLE posts_hot; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.posts_hot TO app_user;


--
-- Name: SEQUENCE posts_raw_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.posts_raw_id_seq TO app_user;


--
-- Name: TABLE quality_metrics; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.quality_metrics TO app_user;


--
-- Name: SEQUENCE quality_metrics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.quality_metrics_id_seq TO app_user;


--
-- Name: TABLE reports; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.reports TO app_user;


--
-- Name: TABLE semantic_audit_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.semantic_audit_logs TO app_user;


--
-- Name: SEQUENCE semantic_audit_logs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.semantic_audit_logs_id_seq TO app_user;


--
-- Name: TABLE semantic_candidates; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.semantic_candidates TO app_user;


--
-- Name: SEQUENCE semantic_candidates_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.semantic_candidates_id_seq TO app_user;


--
-- Name: TABLE semantic_concepts; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.semantic_concepts TO app_user;


--
-- Name: SEQUENCE semantic_concepts_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.semantic_concepts_id_seq TO app_user;


--
-- Name: TABLE semantic_rules; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.semantic_rules TO app_user;


--
-- Name: SEQUENCE semantic_rules_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.semantic_rules_id_seq TO app_user;


--
-- Name: TABLE semantic_terms; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.semantic_terms TO app_user;


--
-- Name: SEQUENCE semantic_terms_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.semantic_terms_id_seq TO app_user;


--
-- Name: TABLE storage_metrics; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.storage_metrics TO app_user;


--
-- Name: SEQUENCE storage_metrics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.storage_metrics_id_seq TO app_user;


--
-- Name: TABLE subreddit_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.subreddit_snapshots TO app_user;


--
-- Name: SEQUENCE subreddit_snapshots_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.subreddit_snapshots_id_seq TO app_user;


--
-- Name: TABLE tasks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.tasks TO app_user;


--
-- Name: TABLE tier_audit_logs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.tier_audit_logs TO app_user;


--
-- Name: SEQUENCE tier_audit_logs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.tier_audit_logs_id_seq TO app_user;


--
-- Name: TABLE tier_suggestions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.tier_suggestions TO app_user;


--
-- Name: SEQUENCE tier_suggestions_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.tier_suggestions_id_seq TO app_user;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.users TO app_user;


--
-- Name: TABLE v_analyses_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.v_analyses_stats TO app_user;


--
-- Name: TABLE vw_community_quality; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.vw_community_quality TO app_user;


--
-- PostgreSQL database dump complete
--

\unrestrict lBf4IsIow6Jaa7SL1faJE1W0J5SnpAz54dKPieylOfYeJp1ZLtrfyRK5hvvamt0

