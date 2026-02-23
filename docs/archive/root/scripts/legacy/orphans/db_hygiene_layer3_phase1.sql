-- Layer 3: Value Scoring - Phase 1 (Fixed)
-- 1. Add Column (in DO block)
-- 2. Populate Baseline Scores (plain SQL)

-- Step 1: Add Column Safely
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'posts_raw' AND column_name = 'value_score') THEN
        ALTER TABLE posts_raw ADD COLUMN value_score SMALLINT;
        RAISE NOTICE 'Column value_score added.';
    END IF;
END $$;

-- Step 2: Populate Scores (Wrapped in Transaction for atomicity)
BEGIN;

-- 规则 1: 垃圾/广告 -> 0分
UPDATE posts_raw
SET value_score = 0
WHERE spam_category IS NOT NULL;

-- 规则 2: 黄金决策 -> 7分
UPDATE posts_raw
SET value_score = 7
WHERE spam_category IS NULL 
  AND metadata->>'value_tier' = 'gold_decision';

-- 规则 3: 黄金痛点 -> 6分
UPDATE posts_raw
SET value_score = 6
WHERE spam_category IS NULL 
  AND metadata->>'value_tier' = 'gold_problem';

-- 规则 4: 普通/其他 -> 3分
UPDATE posts_raw
SET value_score = 3
WHERE spam_category IS NULL 
  AND (metadata->>'value_tier' = 'normal' OR metadata->>'value_tier' IS NULL);

COMMIT;