-- 1. 物理清除 3 个死矿社区
-- 由于外键是 CASCADE 的 (通常)，删除 community_pool 会自动级联删除 posts, comments 等
-- 但为了安全，我们显式删除 posts_raw 和 cache

BEGIN;

DELETE FROM posts_raw WHERE subreddit IN ('r/lazshop_ph', 'r/ecommerceseo', 'r/sellingonamazonfba');
DELETE FROM posts_hot WHERE subreddit IN ('r/lazshop_ph', 'r/ecommerceseo', 'r/sellingonamazonfba');
DELETE FROM community_cache WHERE community_name IN ('r/lazshop_ph', 'r/ecommerceseo', 'r/sellingonamazonfba');
DELETE FROM community_pool WHERE name IN ('r/lazshop_ph', 'r/ecommerceseo', 'r/sellingonamazonfba');

-- 2. 修复脏数据 (去除类别空格)
-- 我们的 categories 是 JSONB 数组 ([" Category"]) 或 字符串 " Category"
-- 针对 JSONB 数组中的每个元素去除空格比较麻烦，但可以用 jsonb_path_query_array 或 简单的 replace

-- 简单粗暴法：将 JSONB 转为 Text，做 Replace，再转回 JSONB
-- 风险：如果空格在 key 里面会被误伤。但我们的 key 是简单的 string。
-- 更好的方法：直接针对已知脏数据进行 Update

UPDATE community_pool
SET categories = jsonb_set(
    categories,
    '{0}',
    to_jsonb(trim(categories->>0))
)
WHERE categories->>0 LIKE ' %' OR categories->>0 LIKE '% ';

COMMIT;
