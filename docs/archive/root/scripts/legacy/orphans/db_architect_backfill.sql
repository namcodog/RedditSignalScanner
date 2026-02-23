-- Architect's Mandated Backfill
-- 确保 100% 覆盖率，无 NULL 值

BEGIN;

UPDATE posts_raw
SET value_score = COALESCE(value_score, 3),
    business_pool = CASE
      WHEN COALESCE(value_score,3) >= 8 THEN 'core'
      WHEN COALESCE(value_score,3) <= 2 THEN 'noise'
      ELSE 'lab' END
WHERE value_score IS NULL OR business_pool IS NULL;

COMMIT;
