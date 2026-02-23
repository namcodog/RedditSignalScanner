-- Migration: Data Backfill from JSONB to Relational Tags
-- Date: 2025-12-02
-- Objective: Parse existing 'categories' JSON array and populate 'community_category_map'

BEGIN;

-- 1. Auto-create any missing categories found in the data (Safety Net)
INSERT INTO business_categories (key, display_name)
SELECT DISTINCT 
    trim(both '"' from jsonb_array_elements(categories)::text) as key,
    trim(both '"' from jsonb_array_elements(categories)::text) as display_name
FROM community_pool
WHERE categories IS NOT NULL 
  AND jsonb_typeof(categories) = 'array'
ON CONFLICT (key) DO NOTHING;

-- 2. Populate the Mapping Table
INSERT INTO community_category_map (community_id, category_key, is_primary)
SELECT DISTINCT
    cp.id,
    trim(both '"' from tag.value::text) as category_key,
    CASE 
        -- Heuristic: If it matches one of our 7 pillars, mark as primary
        WHEN trim(both '"' from tag.value::text) IN (
            'E-commerce_Ops', 'Home_Lifestyle', 'Family_Parenting', 
            'Tools_EDC', 'Food_Coffee_Lifestyle', 'Minimal_Outdoor', 'Frugal_Living'
        ) THEN true 
        ELSE false 
    END as is_primary
FROM community_pool cp,
     jsonb_array_elements(cp.categories) tag
WHERE cp.categories IS NOT NULL 
  AND jsonb_typeof(cp.categories) = 'array'
ON CONFLICT (community_id, category_key) DO NOTHING;

-- 3. Verification
SELECT 'Communities Mapped' as metric, COUNT(DISTINCT community_id) as count FROM community_category_map;
SELECT 'Tags Assigned' as metric, COUNT(*) as count FROM community_category_map;

COMMIT;
