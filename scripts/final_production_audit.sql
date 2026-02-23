-- scripts/final_production_audit.sql
-- 生产数据库终极验收审计脚本
-- 对应文档: docs/sop/数据库开发与使用规范.md (v1.7)

\pset format wrapped
\pset expanded off
\pset border 2

SELECT '开始执行全方位验收审计...' as "Status";

-------------------------------------------------------------------------------
-- 1. 结构合规性检查 (Schema Validation)
-------------------------------------------------------------------------------
SELECT '1. 结构合规性 (Schema Compliance)' as "Section";

WITH checks AS (
    SELECT 'Table: posts_raw' as item, EXISTS(SELECT 1 FROM pg_tables WHERE tablename='posts_raw') as passed
    UNION ALL
    SELECT 'Table: post_embeddings (AI)', EXISTS(SELECT 1 FROM pg_tables WHERE tablename='post_embeddings')
    UNION ALL
    SELECT 'Table: authors (User Profile)', EXISTS(SELECT 1 FROM pg_tables WHERE tablename='authors')
    UNION ALL
    SELECT 'Table: quality_metrics', EXISTS(SELECT 1 FROM pg_tables WHERE tablename='quality_metrics')
    UNION ALL
    SELECT 'Extension: vector', EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')
    UNION ALL
    SELECT 'Trigger: SCD2 Logic', EXISTS(SELECT 1 FROM pg_trigger WHERE tgname='enforce_scd2_posts_raw')
    UNION ALL
    SELECT 'Index: HNSW (AI Search)', EXISTS(SELECT 1 FROM pg_indexes WHERE indexname='idx_post_embeddings_hnsw')
)
SELECT item, 
       CASE WHEN passed THEN '✅ PASS' ELSE '❌ FAIL' END as status 
FROM checks;

-------------------------------------------------------------------------------
-- 2. 一致性约束检查 (Consistency Constraints)
-------------------------------------------------------------------------------
SELECT '2. 一致性约束 (Consistency Constraints)' as "Section";

WITH constraints AS (
    -- 检查 Check 约束定义是否包含 'a-z' 而不包含 'A-Z'
    SELECT 'Constraint: Lowercase Locked (Pool)' as item, 
           EXISTS(SELECT 1 FROM pg_constraint WHERE conname='ck_community_pool_name_format' AND pg_get_constraintdef(oid) LIKE '%a-z0-9_%') as passed
    UNION ALL
    SELECT 'Constraint: Foreign Key (Authors)', 
           EXISTS(SELECT 1 FROM pg_constraint WHERE conname='fk_posts_raw_author')
)
SELECT item, 
       CASE WHEN passed THEN '✅ PASS' ELSE '❌ FAIL' END as status 
FROM constraints;

-------------------------------------------------------------------------------
-- 3. 数据质量实测 (Data Quality Audit)
-------------------------------------------------------------------------------
SELECT '3. 数据质量实测 (Data Quality Audit)' as "Section";

SELECT 
    count(*) as "Banned Uppercase Communities",
    CASE WHEN count(*) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM public.community_pool
WHERE name !~ '^r/[a-z0-9_]+$';

SELECT 
    count(*) as "Garbage AutoMod Posts (Active)",
    CASE WHEN count(*) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM public.posts_raw
WHERE is_deleted = false
  AND (body ILIKE 'Welcome to r/%' OR author_name = 'AutoModerator');

SELECT 
    count(*) as "Orphaned Posts (No Author)",
    CASE WHEN count(*) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status
FROM public.posts_raw p
LEFT JOIN public.authors a ON p.author_id = a.author_id
WHERE p.author_id IS NOT NULL AND p.author_id != '' AND a.author_id IS NULL;

-------------------------------------------------------------------------------
-- 4. 监控指标抽查 (Observability Check)
-------------------------------------------------------------------------------
SELECT '4. 监控指标抽查 (Observability Check)' as "Section";

SELECT date, collection_success_rate, deduplication_rate, updated_at
FROM public.quality_metrics
ORDER BY date DESC
LIMIT 3;

-------------------------------------------------------------------------------
-- 5. 统计概览 (Statistics Overview)
-------------------------------------------------------------------------------
SELECT '5. 统计概览 (Database Stats)' as "Section";

SELECT 
    (SELECT count(*) FROM community_pool) as "Total Communities",
    (SELECT count(*) FROM posts_raw) as "Total Posts",
    (SELECT count(*) FROM authors) as "Total Authors",
    (SELECT count(*) FROM quality_metrics) as "Days Monitored";