/**
 * 社区池相关类型定义
 */

export type Tier = 'T1' | 'T2' | 'T3';
export type Priority = 'high' | 'medium' | 'low';
export type HealthStatus = 'healthy' | 'warning' | 'critical' | 'unknown';

export interface CommunityPoolItem {
  name: string;              // r/xxx
  tier: Tier;
  priority: Priority;
  is_active: boolean;
  daily_posts: number;
  avg_comment_length: number;
  quality_score: number;     // semantic_quality_score
  user_feedback_count: number;
  discovered_count: number;
  health_status: HealthStatus;
  auto_tier_enabled: boolean;
  recent_metrics: {
    posts_7d: number;
    comments_7d: number;
    pain_density_30d: number;
    brand_mentions_30d: number;
  };
  tier_suggestion?: Tier | 'REMOVE' | null;
}

export interface TierSuggestionView {
  community: string;         // r/xxx
  current_tier: string;      // 'T1' | 'T2' | 'T3'
  suggested_tier: string;    // 'T1' | 'T2' | 'T3' | 'REMOVE'
  confidence: number;        // 0~1
  reasons: string[];         // 文案说明
  metrics: Record<string, any>;
  priority_score: number;    // 用于排序
  health_status: string;     // 'healthy' | 'warning' | 'critical'
}

export interface TierSuggestionResponse {
  suggestions: TierSuggestionView[];
  summary: {
    total_suggestions: number;
    promote_to_t1: number;
    promote_to_t2: number;
    demote_to_t3: number;
    remove_from_pool: number;
  };
}

export interface TierSuggestionItem {
  id: number;
  community_name: string;
  current_tier: string;
  suggested_tier: string;
  confidence: number;
  status: string;
  priority_score: number;
  reasons: string[];
  generated_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  applied_at: string | null;
  expires_at: string;
}

export interface TierAuditLogItem {
  id: number;
  community_name: string;
  action: string;
  field_changed: string;
  from_value: string | null;
  to_value: string;
  changed_by: string;
  change_source: 'manual' | 'auto' | 'suggestion';
  reason: string | null;
  snapshot_before: Record<string, unknown>;
  snapshot_after: Record<string, unknown>;
  suggestion_id: number | null;
  is_rolled_back: boolean;
  rolled_back_at: string | null;
  rolled_back_by: string | null;
  created_at: string;
}

export interface BatchUpdatePayload {
  communities: string[];
  updates: {
    tier?: string;
    priority?: string;
    is_active?: boolean;
    downrank_factor?: number;
    auto_tier_enabled?: boolean;
  };
  reason?: string;
}

export interface BatchUpdateResponse {
  updated_count: number;
  communities: string[];
}