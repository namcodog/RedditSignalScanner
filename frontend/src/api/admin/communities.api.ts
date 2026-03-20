import { apiClient } from '../client';

export interface CommunitiesSummaryItem {
  community: string;
  hit_7d: number;
  last_crawled_at: string | null;
  dup_ratio: number;
  spam_ratio: number;
  topic_score: number;
  c_score: number;
  status_color: string;
  labels: string[];
}

export interface CommunitySummaryResponse {
  items: CommunitiesSummaryItem[];
  total: number;
}

export const getCommunitiesSummary = async (params?: {
  q?: string;
  status?: 'green' | 'yellow' | 'red';
  tag?: string;
  sort?: 'cscore_desc' | 'hit_desc';
  page?: number;
  page_size?: number;
}): Promise<CommunitySummaryResponse> => {
  const response = await apiClient.get<CommunitySummaryResponse>('/admin/communities/summary', { params });
  return response.data;
};

export interface EvidencePost {
  source_post_id: string;
  title: string;
  summary: string;
  score: number;
  num_comments: number;
  post_created_at: string;
  evidence_score: number;
  probe_source: string;
  source_query: string;
}

export interface DiscoveredCommunityItem {
  name: string;
  discovered_from_keywords: Record<string, any> | null;
  discovered_count: number;
  first_discovered_at: string;
  last_discovered_at: string;
  status: string;
  evidence_posts: EvidencePost[];
}

export interface DiscoveredCommunitiesResponse {
  items: DiscoveredCommunityItem[];
  total: number;
}

export type DiscoveredCommunitiesParams =
  | number
  | {
      evidence_limit?: number;
    };

export const getDiscoveredCommunities = async (
  paramsOrLimit: DiscoveredCommunitiesParams = {},
): Promise<DiscoveredCommunitiesResponse> => {
  const params =
    typeof paramsOrLimit === 'number'
      ? { evidence_limit: paramsOrLimit }
      : { evidence_limit: paramsOrLimit.evidence_limit ?? 3 };
  const response = await apiClient.get<DiscoveredCommunitiesResponse>('/admin/communities/discovered', {
    params,
  });
  return response.data;
};

export interface ApproveCommunityRequest {
  name: string;
  tier: string;
  categories?: Record<string, any> | null;
  admin_notes?: string | null;
}

export interface ApproveCommunityResponse {
  approved: string;
  pool_is_active: boolean;
}

export const approveCommunity = async (
  payload: ApproveCommunityRequest,
): Promise<ApproveCommunityResponse> => {
  const response = await apiClient.post<ApproveCommunityResponse>('/admin/communities/approve', payload);
  return response.data;
};

export interface RejectCommunityRequest {
  name: string;
  admin_notes?: string | null;
}

export interface RejectCommunityResponse {
  rejected: string;
}

export const rejectCommunity = async (
  payload: RejectCommunityRequest,
): Promise<RejectCommunityResponse> => {
  const response = await apiClient.post<RejectCommunityResponse>('/admin/communities/reject', payload);
  return response.data;
};

export interface CommunityPoolItem {
  name: string;
  tier: string;
  categories: Record<string, any> | string[] | null;
  description_keywords: Record<string, any> | null;
  daily_posts: number;
  avg_comment_length: number;
  quality_score: number;
  priority: string;
  user_feedback_count: number;
  discovered_count: number;
  is_active: boolean;
  health_status: string;
  auto_tier_enabled: boolean;
  recent_metrics: {
    posts_7d: number;
    comments_7d: number;
    pain_density_30d: number;
    brand_mentions_30d: number;
  };
  tier_suggestion: any;
}

export interface CommunityPoolListResponse {
  items: CommunityPoolItem[];
  total: number;
  page: number;
  page_size: number;
}

export const getCommunityPool = async (params: {
  tier?: string;
  priority?: string;
  is_active?: boolean;
  health_status?: string;
  sort_by?: string;
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}): Promise<CommunityPoolListResponse> => {
  const response = await apiClient.get<CommunityPoolListResponse>('/admin/communities/pool', { params });
  return response.data;
};

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

export const batchUpdateCommunities = async (
  payload: BatchUpdatePayload,
): Promise<{ updated_count: number }> => {
  const response = await apiClient.patch<{ updated_count: number }>('/admin/communities/batch', payload);
  return response.data;
};

export const disableCommunity = async (name: string): Promise<{ disabled: string }> => {
  const response = await apiClient.delete<{ disabled: string }>(`/admin/communities/${encodeURIComponent(name)}`);
  return response.data;
};

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
}

export const getTierSuggestions = async (params: {
  community_name?: string;
  status?: string;
  min_confidence?: number;
  page?: number;
  page_size?: number;
}): Promise<{ items: TierSuggestionItem[]; total: number }> => {
  const response = await apiClient.get('/admin/communities/tier-suggestions', { params });
  return response.data;
};

export const generateTierSuggestions = async (
  payload: { thresholds?: any; target_communities?: string[] } = {},
): Promise<any> => {
  const response = await apiClient.post('/admin/communities/suggest-tier-adjustments', payload);
  return response.data;
};

export const applyTierSuggestions = async (
  payload: { suggestion_ids: number[] },
): Promise<{ applied_count: number }> => {
  const response = await apiClient.post('/admin/communities/apply-suggestions', payload);
  return response.data;
};

export interface TierAuditLogItem {
  id: number;
  community_name: string;
  action: string;
  field_changed: string;
  from_value: string;
  to_value: string;
  changed_by: string;
  change_source: string;
  reason?: string;
  created_at: string;
  is_rolled_back: boolean;
}

export const getCommunityAuditLogs = async (
  name: string,
  params: { page?: number; page_size?: number },
): Promise<{ items: TierAuditLogItem[]; total: number }> => {
  const response = await apiClient.get(`/admin/communities/${name}/tier-audit-logs`, { params });
  return response.data;
};

export const rollbackCommunity = async (auditLogId: number, reason: string): Promise<any> => {
  const response = await apiClient.post('/admin/communities/rollback', {
    audit_log_id: auditLogId,
    reason,
  });
  return response.data;
};
