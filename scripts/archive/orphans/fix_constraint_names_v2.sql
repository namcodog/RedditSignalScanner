-- 数据库约束命名规范治理脚本 V2
-- 目标：消除重复的表名前缀，统一命名风格，处理冗余约束
-- 运行环境：reddit_signal_scanner_test (测试库)

BEGIN;

-- ==========================================
-- 1. Community Cache 表 (无冲突，直接重命名)
-- ==========================================
ALTER TABLE public.community_cache 
    RENAME CONSTRAINT "ck_community_cache_ck_community_cache_positive_ttl" TO "ck_community_cache_ttl_positive";

ALTER TABLE public.community_cache 
    RENAME CONSTRAINT "ck_community_cache_ck_community_cache_posts_cached_non_negative" TO "ck_community_cache_posts_cached_nonneg";

ALTER TABLE public.community_cache 
    RENAME CONSTRAINT "ck_community_cache_ck_community_cache_priority_range" TO "ck_community_cache_priority_range";

ALTER TABLE public.community_cache 
    RENAME CONSTRAINT "ck_community_cache_ck_community_cache_name_format" TO "ck_community_cache_name_format";

ALTER TABLE public.community_cache 
    RENAME CONSTRAINT "ck_community_cache_ck_community_cache_member_count_non_negative" TO "ck_community_cache_member_count_nonneg";

-- ==========================================
-- 2. Community Pool 表 (无冲突，直接重命名)
-- ==========================================
ALTER TABLE public.community_pool 
    RENAME CONSTRAINT "ck_community_pool_ck_community_pool_name_len" TO "ck_community_pool_name_len";

ALTER TABLE public.community_pool 
    RENAME CONSTRAINT "ck_community_pool_ck_community_pool_name_format" TO "ck_community_pool_name_format";

-- ==========================================
-- 3. Posts Raw 表 (无冲突，直接重命名)
-- ==========================================
ALTER TABLE public.posts_raw 
    RENAME CONSTRAINT "ck_posts_raw_ck_posts_raw_version_positive" TO "ck_posts_raw_version_positive";

ALTER TABLE public.posts_raw 
    RENAME CONSTRAINT "ck_posts_raw_ck_posts_raw_valid_period" TO "ck_posts_raw_valid_period";

-- ==========================================
-- 4. Comments 表 (无冲突，直接重命名)
-- ==========================================
ALTER TABLE public.comments 
    RENAME CONSTRAINT "ck_comments_ck_comments_depth_non_negative" TO "ck_comments_depth_nonneg";

-- ==========================================
-- 5. Tasks 表 (处理冲突与冗余)
-- ==========================================

-- 5.1 Description Length: 只有一个，直接重命名
ALTER TABLE public.tasks 
    RENAME CONSTRAINT "ck_tasks_ck_tasks_valid_description_length" TO "ck_tasks_desc_len";

-- 5.2 Completion Time: 存在两个不同逻辑的约束，重命名丑的那个以区分
-- 旧名: ck_tasks_ck_tasks_valid_completion_time (逻辑: >= created_at)
-- 存在: ck_tasks_valid_completion_time (逻辑: >= started_at)
ALTER TABLE public.tasks 
    RENAME CONSTRAINT "ck_tasks_ck_tasks_valid_completion_time" TO "ck_tasks_completed_after_created";

-- 5.3 Error Message: 存在逻辑重复的约束，删除丑的
ALTER TABLE public.tasks 
    DROP CONSTRAINT IF EXISTS "ck_tasks_ck_tasks_error_message_when_failed";

-- 5.4 Status Alignment: 存在逻辑重复的约束，删除丑的
ALTER TABLE public.tasks 
    DROP CONSTRAINT IF EXISTS "ck_tasks_ck_tasks_completed_status_alignment";

-- ==========================================
-- 6. Users 表 (无冲突，直接重命名)
-- ==========================================
ALTER TABLE public.users 
    RENAME CONSTRAINT "ck_users_ck_users_valid_email" TO "ck_users_valid_email";

ALTER TABLE public.users 
    RENAME CONSTRAINT "ck_users_ck_users_membership_level" TO "ck_users_membership_level";

COMMIT;
