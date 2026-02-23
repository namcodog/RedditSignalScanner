-- 侦查脚本：寻找垃圾信号
-- 运行方式：psql -f backend/scripts/scout_noise.sql

\echo '--- 1. 标题重复Top 10 (可能是广告群发) ---'
SELECT title, COUNT(*) as cnt, MAX(subreddit) as sample_sub
FROM posts_raw
WHERE created_at > NOW() - INTERVAL '1 year'
GROUP BY title
HAVING COUNT(*) > 5
ORDER BY cnt DESC
LIMIT 10;

\echo '\n--- 2. 负分贴(Score < 0)中的高频词 ---'
-- 这是一个简化的词频统计，利用 tsvector
WITH negative_posts AS (
    SELECT to_tsvector('english', title || ' ' || COALESCE(body, '')) as tsv
    FROM posts_raw
    WHERE score < 0 AND created_at > NOW() - INTERVAL '3 months'
    LIMIT 1000
),
stats AS (
    SELECT word, nentry
    FROM ts_stat('SELECT tsv FROM negative_posts')
)
SELECT word, nentry
FROM stats
WHERE word NOT IN ('the', 'to', 'and', 'of', 'in', 'is', 'for', 'this', 'that', 'it', 'on', 'with', 'are', 'as', 'be', 'was', 'have', 'but', 'not', 'my', 'you', 'your', 'so', 'just', 'like', 'can', 'or', 'at', 'if', 'me', 'about', 'an')
AND length(word) > 3
ORDER BY nentry DESC
LIMIT 20;

\echo '\n--- 3. 包含典型垃圾词的帖子数量 ---\n'
SELECT 
    SUM(CASE WHEN title ILIKE '%crypto%' OR body ILIKE '%crypto%' THEN 1 ELSE 0 END) as crypto,
    SUM(CASE WHEN title ILIKE '%nft%' OR body ILIKE '%nft%' THEN 1 ELSE 0 END) as nft,
    SUM(CASE WHEN title ILIKE '%onlyfans%' OR body ILIKE '%onlyfans%' THEN 1 ELSE 0 END) as onlyfans,
    SUM(CASE WHEN title ILIKE '%discount%' OR body ILIKE '%discount%' THEN 1 ELSE 0 END) as discount,
    SUM(CASE WHEN title ILIKE '%giveaway%' OR body ILIKE '%giveaway%' THEN 1 ELSE 0 END) as giveaway
FROM posts_raw
WHERE created_at > NOW() - INTERVAL '1 year';
