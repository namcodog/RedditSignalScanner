-- Layer 4: The Three Pools (Fix & Backfill)
-- 1. Set Timeout
-- 2. Backfill Data

-- 临时调大超时限制到 10 分钟
SET statement_timeout = 600000;

BEGIN;

-- 1. Noise Pool (<= 2 or Spam)
UPDATE posts_raw
SET business_pool = 'noise'
WHERE (value_score <= 2 OR spam_category IS NOT NULL) AND business_pool IS NULL;

-- 2. Core Pool (>= 8)
UPDATE posts_raw
SET business_pool = 'core'
WHERE value_score >= 8 AND business_pool IS NULL;

-- 3. Lab Pool (The Rest: 3-7)
UPDATE posts_raw
SET business_pool = 'lab'
WHERE business_pool IS NULL;

COMMIT;

-- 验证结果
SELECT business_pool, value_score, COUNT(*) 
FROM posts_raw 
GROUP BY 1, 2 
ORDER BY 2 DESC, 1;
