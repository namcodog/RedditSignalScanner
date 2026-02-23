-- Phase 3: Community Control Tower
-- 1. Status Machine (active/paused/banned)
-- 2. Value Metrics (feedback loop)

BEGIN;

-- ==========================================
-- 1. Add Status Machine
-- ==========================================

ALTER TABLE public.community_pool
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

-- Constraint check
ALTER TABLE public.community_pool
ADD CONSTRAINT ck_community_pool_status 
CHECK (status IN ('active', 'paused', 'banned'));

COMMENT ON COLUMN public.community_pool.status IS '状态机: active(正常), paused(暂缓), banned(拉黑)';

-- Migrate Data (Booleans -> Status Enum)
-- 1. First, set everyone to 'paused' if not active
UPDATE public.community_pool 
SET status = 'paused' 
WHERE is_active = false;

-- 2. Set 'active' (Default was active, but be explicit)
UPDATE public.community_pool 
SET status = 'active' 
WHERE is_active = true;

-- 3. Overwrite with 'banned' if blacklisted (Priority High)
UPDATE public.community_pool 
SET status = 'banned' 
WHERE is_blacklisted = true;

-- ==========================================
-- 2. Add Value Metrics (The Feedback Loop)
-- ==========================================

ALTER TABLE public.community_pool
ADD COLUMN IF NOT EXISTS core_post_ratio NUMERIC(5,4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_value_score NUMERIC(4,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS recent_core_posts_30d INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS stats_updated_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN public.community_pool.core_post_ratio IS '含金量: Core贴占比 (0.0-1.0)';
COMMENT ON COLUMN public.community_pool.avg_value_score IS '平均价值分 (0-10)';
COMMENT ON COLUMN public.community_pool.recent_core_posts_30d IS '最近30天产出的Core贴数量';

-- ==========================================
-- 3. Bonus: Initial Stats Calculation
-- ==========================================
-- 计算并回填初始指标 (基于现有数据)

WITH stats AS (
    SELECT 
        p.community_id,
        COUNT(*) FILTER (WHERE p.business_pool = 'core') AS core_count,
        COUNT(*) AS total_count,
        AVG(p.value_score) AS avg_score,
        COUNT(*) FILTER (WHERE p.business_pool = 'core' AND p.created_at > NOW() - INTERVAL '30 days') AS recent_core
    FROM public.posts_raw p
    WHERE p.community_id IS NOT NULL 
      AND p.is_current = true
    GROUP BY p.community_id
)
UPDATE public.community_pool cp
SET 
    core_post_ratio = CASE WHEN s.total_count > 0 THEN ROUND((s.core_count::numeric / s.total_count), 4) ELSE 0 END,
    avg_value_score = ROUND(s.avg_score, 2),
    recent_core_posts_30d = s.recent_core,
    stats_updated_at = NOW()
FROM stats s
WHERE cp.id = s.community_id;

COMMIT;
