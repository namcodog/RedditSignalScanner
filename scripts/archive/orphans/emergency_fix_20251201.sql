-- Emergency Fix: Restore Community Pool Structure & Content
-- Date: 2025-12-01
-- Objective: 
-- 1. Fix 'categories' column type mismatch (Object -> Array) to match codebase expectations.
-- 2. Resurrect critical e-commerce communities that were accidentally wiped but have data in posts_raw.

BEGIN;

-- Step 1: Flatten 'categories' from JSON Object to JSON Array
-- Example: {"business_category": "E-commerce_Ops", ...} -> ["E-commerce_Ops", "高价值社区"]
UPDATE community_pool
SET categories = (
    SELECT jsonb_agg(value)
    FROM jsonb_each_text(categories)
    WHERE key IN ('business_category', 'tier_name') -- Only keep relevant tags
)
WHERE jsonb_typeof(categories) = 'object';

-- Step 1.1: Ensure no nulls in categories (convert null to empty array if any)
UPDATE community_pool
SET categories = '["Uncategorized"]'::jsonb
WHERE categories IS NULL OR jsonb_array_length(categories) = 0;


-- Step 2: Resurrect Ghost Communities
-- Find communities present in posts_raw (with > 50 posts) but missing from community_pool
WITH ghosts AS (
    SELECT 
        p.subreddit, 
        COUNT(*) as post_count
    FROM posts_raw p
    LEFT JOIN community_pool c ON p.subreddit = c.name
    WHERE c.id IS NULL
    GROUP BY p.subreddit
    HAVING COUNT(*) > 50
)
INSERT INTO community_pool (
    name, 
    tier, 
    categories, 
    is_active, 
    priority, 
    semantic_quality_score, 
    description_keywords,
    created_at,
    updated_at
)
SELECT 
    g.subreddit,
    'high',                            -- Default to High tier for recovered data
    '["E-commerce_Ops", "Recovered"]'::jsonb, -- Default category
    true,                              -- Active
    'high',                            -- High Priority
    0.9,                               -- High score to prevent auto-pruning
    '{"recovery_reason": "post_disaster_fix"}'::jsonb,
    NOW(),
    NOW()
FROM ghosts g
ON CONFLICT (name) DO NOTHING;

-- Step 3: Verification Output
SELECT 'Recovered Communities' as metric, COUNT(*) as count FROM community_pool WHERE categories @> '["Recovered"]';

COMMIT;
