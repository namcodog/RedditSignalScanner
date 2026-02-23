-- 数据库约束命名规范治理脚本 V3 (Production Safe)
-- 目标：幂等地重命名约束，跳过不存在的
-- 运行环境：生产库 (reddit_signal_scanner)

BEGIN;

DO $$
BEGIN

    -- 1. Community Cache
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_community_cache_ck_community_cache_member_count_non_negative') THEN
        ALTER TABLE public.community_cache RENAME CONSTRAINT "ck_community_cache_ck_community_cache_member_count_non_negative" TO "ck_community_cache_member_count_nonneg";
    END IF;

    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_community_cache_ck_community_cache_name_format') THEN
        -- 注意：如果目标名字已存在，这里可能会报错，所以生产脚本需要更小心
        -- 检查目标名字是否存在
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_community_cache_name_format') THEN
            ALTER TABLE public.community_cache RENAME CONSTRAINT "ck_community_cache_ck_community_cache_name_format" TO "ck_community_cache_name_format";
        END IF;
    END IF;

    -- 2. Community Pool
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_community_pool_ck_community_pool_name_len') THEN
        ALTER TABLE public.community_pool RENAME CONSTRAINT "ck_community_pool_ck_community_pool_name_len" TO "ck_community_pool_name_len";
    END IF;

    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_community_pool_ck_community_pool_name_format') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_community_pool_name_format') THEN
            ALTER TABLE public.community_pool RENAME CONSTRAINT "ck_community_pool_ck_community_pool_name_format" TO "ck_community_pool_name_format";
        END IF;
    END IF;
    
    -- 3. Comments
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_comments_ck_comments_depth_non_negative') THEN
        ALTER TABLE public.comments RENAME CONSTRAINT "ck_comments_ck_comments_depth_non_negative" TO "ck_comments_depth_nonneg";
    END IF;

    -- 4. Tasks
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_tasks_error_message_when_failed') THEN
        ALTER TABLE public.tasks RENAME CONSTRAINT "ck_tasks_error_message_when_failed" TO "ck_tasks_error_msg_failed";
    END IF;
    
    -- 5. Users
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_ck_users_membership_level') THEN
        ALTER TABLE public.users RENAME CONSTRAINT "ck_users_ck_users_membership_level" TO "ck_users_membership_level";
    END IF;

END $$;

COMMIT;
