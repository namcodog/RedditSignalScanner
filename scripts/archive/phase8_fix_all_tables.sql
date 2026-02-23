-- scripts/phase8_fix_all_tables.sql
-- Phase 8: 全库格式统一修复 (Grand Unification) - With Timeout Extension
-- 目标：修复 comments 和 posts_hot 表的 subreddit 格式，并锁死约束。

BEGIN;

-- 临时增加超时时间至 5 分钟
SET LOCAL statement_timeout = '300s';

-- 1. 修复 comments 表 (118w rows)
-- 这是一个大表操作，可能需要一点时间
UPDATE public.comments
SET subreddit = 'r/' || LOWER(subreddit)
WHERE subreddit NOT LIKE 'r/%';

UPDATE public.comments
SET subreddit = LOWER(subreddit)
WHERE subreddit LIKE 'r/%' AND subreddit != LOWER(subreddit);

-- 2. 修复 posts_hot 表 (2.7w rows)
UPDATE public.posts_hot
SET subreddit = 'r/' || LOWER(subreddit)
WHERE subreddit NOT LIKE 'r/%';

UPDATE public.posts_hot
SET subreddit = LOWER(subreddit)
WHERE subreddit LIKE 'r/%' AND subreddit != LOWER(subreddit);

-- 3. 锁死约束 (Lock Down)
-- comments 表
ALTER TABLE public.comments DROP CONSTRAINT IF EXISTS ck_comments_subreddit_format;
ALTER TABLE public.comments 
    ADD CONSTRAINT ck_comments_subreddit_format 
    CHECK (subreddit ~ '^r/[a-z0-9_]+$');

-- posts_hot 表
ALTER TABLE public.posts_hot DROP CONSTRAINT IF EXISTS ck_posts_hot_subreddit_format;
ALTER TABLE public.posts_hot 
    ADD CONSTRAINT ck_posts_hot_subreddit_format 
    CHECK (subreddit ~ '^r/[a-z0-9_]+$');

COMMIT;
