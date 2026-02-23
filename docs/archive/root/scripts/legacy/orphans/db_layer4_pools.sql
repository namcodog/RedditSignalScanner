-- Layer 4: The Three Pools (Implementation)
-- 1. Add Column
-- 2. Backfill Data
-- 3. Update Trigger

-- Step 1: Add Column & Index
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'posts_raw' AND column_name = 'business_pool') THEN
        ALTER TABLE posts_raw ADD COLUMN business_pool VARCHAR(10);
        RAISE NOTICE 'Column business_pool added.';
    END IF;
END $$;

-- Index (Concurrent check not needed for single run usually, but safer)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_raw_business_pool ON posts_raw(business_pool); 
-- (Will run index creation separately to avoid transaction block issues)

-- Step 2: Backfill Data (Based on existing scores)
BEGIN;

-- Noise Pool (<= 2 or Spam)
UPDATE posts_raw
SET business_pool = 'noise'
WHERE value_score <= 2 OR spam_category IS NOT NULL;

-- Core Pool (>= 8)
UPDATE posts_raw
SET business_pool = 'core'
WHERE value_score >= 8;

-- Lab Pool (The Rest: 3-7)
UPDATE posts_raw
SET business_pool = 'lab'
WHERE business_pool IS NULL; -- Catch-all for remaining

RAISE NOTICE '✅ Three Pools populated.';

COMMIT;
