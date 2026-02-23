-- 生产同步：阶段四 4.2 (评论清洗)
-- 目标：清洗 300万+ 评论
-- 运行环境：生产库

BEGIN;
SET statement_timeout = 0; -- 禁用超时

UPDATE comments
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

COMMIT;
