-- 社区归档治理脚本
-- 目标：将长期不活跃/从未抓取的社区标记为归档状态
-- 运行环境：生产库

BEGIN;

-- 1. 创建临时表锁定要归档的社区 (以免误伤)
CREATE TEMP TABLE to_archive AS
SELECT p.id, p.name
FROM community_pool p
LEFT JOIN community_cache c ON p.name = c.community_name
WHERE 
    p.is_active = true -- 只处理当前活跃的
    AND (
        -- 条件 A: 从未抓取过 (僵尸)
        c.last_crawled_at IS NULL
        OR
        -- 条件 B: 超过 30 天没抓取，且不是重要社区
        (c.last_crawled_at < NOW() - INTERVAL '30 days' AND p.tier NOT IN ('high', 'semantic', 'S'))
    );

-- 2. 执行归档更新
UPDATE community_pool
SET 
    is_active = false,              -- 关闭激活
    health_status = 'archived',     -- 状态标记
    tier = 'archived',              -- 分级归档
    priority = 'low',               -- 优先级最低
    updated_at = NOW()
WHERE id IN (SELECT id FROM to_archive);

-- 3. 输出结果报告
DO $$
DECLARE
    archived_count INT;
BEGIN
    SELECT COUNT(*) INTO archived_count FROM to_archive;
    RAISE NOTICE '已成功归档 % 个僵尸社区。', archived_count;
END $$;

COMMIT;
