-- Normalization: Enforce 7 Pillars & Assign Orphans
-- Date: 2025-12-02

BEGIN;

-- 1. Ensure all 'Recovered' or 'High_Value' communities get assigned to 'E-commerce_Ops' if they lack a pillar
-- Logic: If a community has a map to 'Recovered'/'High_Value'/'高价值社区' BUT NO map to the 7 Pillars, add 'E-commerce_Ops'.

INSERT INTO community_category_map (community_id, category_key, is_primary)
SELECT DISTINCT 
    map.community_id, 
    'E-commerce_Ops', 
    true
FROM community_category_map map
WHERE map.category_key IN ('Recovered', 'High_Value', '高价值社区', 'New_Import')
  AND NOT EXISTS (
      SELECT 1 FROM community_category_map sub
      WHERE sub.community_id = map.community_id
        AND sub.category_key IN (
            'E-commerce_Ops', 'Home_Lifestyle', 'Family_Parenting', 
            'Tools_EDC', 'Food_Coffee_Lifestyle', 'Minimal_Outdoor', 'Frugal_Living'
        )
  )
ON CONFLICT (community_id, category_key) DO NOTHING;


-- 2. Delete non-standard categories from the Map
-- This strictly enforces that only the 7 Pillars remain as "Business Categories".
DELETE FROM community_category_map
WHERE category_key NOT IN (
    'E-commerce_Ops', 'Home_Lifestyle', 'Family_Parenting', 
    'Tools_EDC', 'Food_Coffee_Lifestyle', 'Minimal_Outdoor', 'Frugal_Living'
);

-- 3. Delete non-standard keys from the Dictionary
DELETE FROM business_categories
WHERE key NOT IN (
    'E-commerce_Ops', 'Home_Lifestyle', 'Family_Parenting', 
    'Tools_EDC', 'Food_Coffee_Lifestyle', 'Minimal_Outdoor', 'Frugal_Living'
);

-- 4. Verification
SELECT 'Final Community Count' as metric, COUNT(DISTINCT community_id) as val FROM community_category_map;
SELECT 'Final Category Count' as metric, COUNT(*) as val FROM business_categories;

COMMIT;
