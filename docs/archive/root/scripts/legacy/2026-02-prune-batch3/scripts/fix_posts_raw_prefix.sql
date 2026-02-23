-- scripts/fix_posts_raw_prefix.sql
-- 修复 posts_raw 表中缺失 'r/' 前缀的问题，并添加约束锁死
-- 对应 SOP 4.1 规范

BEGIN;

-- 1. 数据修复：补全前缀并转小写
-- 只有当不以 'r/' 开头时才补全
UPDATE public.posts_raw
SET subreddit = 'r/' || LOWER(subreddit)
WHERE subreddit NOT LIKE 'r/%';

-- 2. 数据修复：已有前缀但有大写的，转小写
UPDATE public.posts_raw
SET subreddit = LOWER(subreddit)
WHERE subreddit LIKE 'r/%' AND subreddit != LOWER(subreddit);

-- 3. 漏洞封堵：添加 Check 约束
-- 确保以后进来的数据必须符合 r/lowercase 格式
ALTER TABLE public.posts_raw DROP CONSTRAINT IF EXISTS ck_posts_raw_subreddit_format;
ALTER TABLE public.posts_raw 
    ADD CONSTRAINT ck_posts_raw_subreddit_format 
    CHECK (subreddit ~ '^r/[a-z0-9_]+$');

COMMIT;
