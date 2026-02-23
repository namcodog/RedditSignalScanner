-- Final Step: 补全电商分类
-- 目标：将遗留的核心社区统一归类为 E-commerce_Ops

BEGIN;

UPDATE community_pool
SET 
    categories = jsonb_set(
        COALESCE(categories, '{}'::jsonb), 
        '{business_category}', 
        '"E-commerce_Ops"'
    ),
    updated_at = NOW()
WHERE 
    (categories->>'business_category') IS NULL 
    OR (categories->>'business_category') = '';

-- 验证结果
DO $$
DECLARE
    updated_count INT;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE '已将 % 个遗留社区归类为 E-commerce_Ops。', updated_count;
END $$;

COMMIT;
