-- 草案：facts 质量审计表（示例，不可直接执行）
CREATE TABLE IF NOT EXISTS facts_quality_audit (
    run_id uuid PRIMARY KEY,
    topic text NOT NULL,
    days int NOT NULL,
    mode text NOT NULL,
    config_hash text,
    trend_source text,
    trend_degraded boolean,
    time_window_used int,
    comments_count int,
    posts_count int,
    solutions_count int,
    community_coverage int,
    degraded boolean,
    data_fallback boolean,
    posts_fallback boolean,
    solutions_fallback boolean,
    dynamic_whitelist jsonb,
    dynamic_blacklist jsonb,
    insufficient_flags jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_facts_quality_created_at ON facts_quality_audit(created_at DESC);

-- 保持向前兼容的变更（可重复执行，安全）：
ALTER TABLE facts_quality_audit ADD COLUMN IF NOT EXISTS trend_source text;
ALTER TABLE facts_quality_audit ADD COLUMN IF NOT EXISTS trend_degraded boolean;
