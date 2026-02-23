-- Phase 4: Audit & Noise Gap Closing
-- 1. Create Unified Data Audit Table
-- 2. Expand Noise Categories for "Negative Sample Vault"

BEGIN;

-- ==========================================
-- 1. Unified Data Audit (The Black Box)
-- ==========================================
-- Logs granular events: 'promote_core', 'downgrade_community', 'flag_noise'

CREATE TABLE IF NOT EXISTS public.data_audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- e.g., 'ai_promotion', 'manual_override', 'trigger_reject'
    target_type VARCHAR(20) NOT NULL, -- 'post', 'community', 'report'
    target_id VARCHAR(100) NOT NULL,  -- flexible ID storage
    old_value JSONB,                  -- Snapshot before change
    new_value JSONB,                  -- Snapshot after change
    reason TEXT,
    source_component VARCHAR(50),     -- 'trg_auto_score', 'script_t1_scorer'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_audit_target ON public.data_audit_events(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_data_audit_event ON public.data_audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_data_audit_created ON public.data_audit_events(created_at DESC);

COMMENT ON TABLE public.data_audit_events IS '统一数据审计表：记录数据生命周期中的关键变动 (Promote/Demote/Reject)';

-- ==========================================
-- 2. Expand Noise Labels (The Negative Vault)
-- ==========================================
-- Add user-requested categories for better ML training

ALTER TABLE public.noise_labels 
DROP CONSTRAINT IF EXISTS noise_labels_noise_type_check;

ALTER TABLE public.noise_labels 
ADD CONSTRAINT noise_labels_noise_type_check 
CHECK (noise_type IN (
    -- Legacy (Keep for compatibility)
    'employee_rant', 'resale', 'bot', 'automod', 'template', 'spam_manual', 'offtopic', 'low_quality',
    -- New (User Requested)
    'pure_social',  -- 纯社交/闲聊
    'rage_rant',    -- 情绪宣泄
    'meme_only',    -- 梗图/表情包
    'ultra_short'   -- 极短内容 (Moved from simple rejection to labeled noise)
));

COMMENT ON TABLE public.noise_labels IS '负样本金库：用于存储和训练的已标记噪音数据';

COMMIT;
