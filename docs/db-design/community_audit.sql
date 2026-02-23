-- 草案：社区审计/降权记录（示例，不可直接执行）
CREATE TABLE IF NOT EXISTS community_audit (
    id serial PRIMARY KEY,
    community_id bigint NOT NULL REFERENCES community_pool(id),
    action text NOT NULL CHECK (action IN ('promote','demote','blacklist','restore')),
    metrics jsonb,
    reason text,
    actor text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_community_audit_comm_time ON community_audit(community_id, created_at DESC);
