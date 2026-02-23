-- scripts/phase7_cleanup_community_pool.sql
-- Phase 7: 社区池大清洗 (The Great Purge)
-- 目标：剔除 11-28 00:08 误导入的 1099 个通用技术社区，复活 11-24 的核心电商社区。

BEGIN;

-- 1. 执行软删除 (Purge Intruders)
-- 逻辑：所有在 2025-11-28 00:00 到 00:30 之间创建的，都是入侵者。
UPDATE public.community_pool
SET is_active = false,
    tier = 'archived',
    health_status = 'bulk_import_error',
    priority = 99
WHERE created_at >= '2025-11-28 00:00:00' 
  AND created_at < '2025-11-28 00:30:00'
  AND is_active = true;

-- 2. 清理相关缓存 (Purge Cache)
-- 将已归档社区从缓存表中移除，避免占用爬虫名额
DELETE FROM public.community_cache
WHERE community_name IN (
    SELECT name FROM public.community_pool WHERE health_status = 'bulk_import_error'
);

-- 3. 复活核心资产 (Revive Core)
-- 逻辑：11-25 之前的所有社区（93个），强制激活并设为最高优先级
UPDATE public.community_pool
SET is_active = true,
    tier = 'high',  -- 统一提升为 T1，确保被重视
    priority = 1,   -- 最高优先级
    health_status = 'active' -- 重置健康状态
WHERE created_at < '2025-11-25 00:00:00';

-- 4. 确保 Semantic 也是激活的
UPDATE public.community_pool
SET is_active = true,
    priority = 10 -- 稍低优先级
WHERE created_at >= '2025-11-28 00:50:00' 
  AND created_at < '2025-11-28 01:00:00';

COMMIT;
