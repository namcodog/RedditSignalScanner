-- 数据库约束命名规范治理脚本
-- 目标：消除重复的表名前缀，统一命名风格
-- 运行环境：reddit_signal_scanner_test (测试库)

BEGIN;

-- 1. Community Cache 表
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

-- 2. Community Pool 表
ALTER TABLE public.community_pool 
    RENAME CONSTRAINT "ck_community_pool_ck_community_pool_name_len" TO "ck_community_pool_name_len";

ALTER TABLE public.community_pool 
    RENAME CONSTRAINT "ck_community_pool_ck_community_pool_name_format" TO "ck_community_pool_name_format";

-- 3. Posts Raw 表
ALTER TABLE public.posts_raw 
    RENAME CONSTRAINT "ck_posts_raw_ck_posts_raw_version_positive" TO "ck_posts_raw_version_positive";

ALTER TABLE public.posts_raw 
    RENAME CONSTRAINT "ck_posts_raw_ck_posts_raw_valid_period" TO "ck_posts_raw_valid_period";

-- 4. Comments 表
ALTER TABLE public.comments 
    RENAME CONSTRAINT "ck_comments_ck_comments_depth_non_negative" TO "ck_comments_depth_nonneg";

-- 5. Tasks 表
ALTER TABLE public.tasks 
    RENAME CONSTRAINT "ck_tasks_ck_tasks_valid_description_length" TO "ck_tasks_desc_len";

ALTER TABLE public.tasks 
    RENAME CONSTRAINT "ck_tasks_ck_tasks_valid_completion_time" TO "ck_tasks_valid_completion_time";

ALTER TABLE public.tasks 
    RENAME CONSTRAINT "ck_tasks_ck_tasks_error_message_when_failed" TO "ck_tasks_error_msg_failed";

ALTER TABLE public.tasks 
    RENAME CONSTRAINT "ck_tasks_ck_tasks_completed_status_alignment" TO "ck_tasks_status_alignment";

-- 6. Users 表
ALTER TABLE public.users 
    RENAME CONSTRAINT "ck_users_ck_users_valid_email" TO "ck_users_valid_email";

ALTER TABLE public.users 
    RENAME CONSTRAINT "ck_users_ck_users_membership_level" TO "ck_users_membership_level";

COMMIT;
