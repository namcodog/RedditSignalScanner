// Frontend API Definition for Admin
// Based on backend/app/api/legacy/admin.py and admin_community_pool.py
// SSOT: Backend Legacy API

import { apiClient } from './client';

// --- Dashboard ---

export interface DashboardStats {
  total_users: number;
  total_tasks: number;
  tasks_today: number;
  tasks_completed_today: number;
  avg_processing_time: number;
  cache_hit_rate: number;
  active_workers: number;
  pipeline_health: Record<string, any>;
}

export const getAdminDashboardStats = async (): Promise<DashboardStats> => {
  // Client interceptor unwraps { code: 0, data: ... } -> returns data
  const response = await apiClient.get<DashboardStats>('/admin/dashboard/stats');
  return response.data;
};

// --- Discovered Communities (Candidates) ---

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

export const getDiscoveredCommunities = async (evidenceLimit: number = 3): Promise<DiscoveredCommunitiesResponse> => {
  const response = await apiClient.get<DiscoveredCommunitiesResponse>('/admin/communities/discovered', {
    params: { evidence_limit: evidenceLimit },
  });
  return response.data;
};

export interface ApproveCommunityRequest {
  name: string;
  tier: string; // "medium" by default
  categories?: Record<string, any> | null;
  admin_notes?: string | null;
}

export const approveCommunity = async (payload: ApproveCommunityRequest): Promise<void> => {
  await apiClient.post('/admin/communities/approve', payload);
};

export interface RejectCommunityRequest {
  name: string;
  admin_notes?: string | null;
}

export const rejectCommunity = async (payload: RejectCommunityRequest): Promise<void> => {
  await apiClient.post('/admin/communities/reject', payload);
};

// --- Community Pool ---

export interface CommunityPoolItem {
  name: string;
  tier: string;
  categories: Record<string, any>;
  description_keywords: Record<string, any>;
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
  tier_suggestion: any; // Simplified for now
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

export const batchUpdateCommunities = async (payload: BatchUpdatePayload): Promise<{ updated_count: number }> => {
  const response = await apiClient.patch<{ updated_count: number }>('/admin/communities/batch', payload);
  return response.data;
};

// --- Tier Suggestions & Audit Logs ---

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

export const generateTierSuggestions = async (payload: { thresholds?: any; target_communities?: string[] } = {}): Promise<any> => {
  const response = await apiClient.post('/admin/communities/suggest-tier-adjustments', payload);
  return response.data;
};

export const applyTierSuggestions = async (payload: { suggestion_ids: number[] }): Promise<{ applied_count: number }> => {
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

export const getCommunityAuditLogs = async (name: string, params: { page?: number; page_size?: number }): Promise<{ items: TierAuditLogItem[]; total: number }> => {
  const response = await apiClient.get(`/admin/communities/${name}/tier-audit-logs`, { params });
  return response.data;
};

export const rollbackCommunity = async (auditLogId: number, reason: string): Promise<any> => {
  const response = await apiClient.post('/admin/communities/rollback', { audit_log_id: auditLogId, reason });
  return response.data;
};

// --- Community Import (Excel) ---

export const downloadTemplate = async (): Promise<void> => {
  const response = await apiClient.get('/admin/communities/template', {
    responseType: 'blob',
  });
  
  // Create a link to download the file
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'community_template.xlsx');
  document.body.appendChild(link);
  link.click();
  
  // Clean up
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const importCommunities = async (file: File, dryRun: boolean = false): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/admin/communities/import', formData, {
    params: { dry_run: dryRun },
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export interface CommunityImportSummary {
  total: number;
  valid: number;
  invalid: number;
  duplicates: number;
  imported: number;
}

export interface ImportHistoryItem {
  id: number;
  filename: string;
  status: string; // 'pending', 'processing', 'completed', 'failed'
  uploaded_by: string;
  uploaded_at: string;
  dry_run: boolean;
  summary: CommunityImportSummary;
  error_log?: string; 
}

export const getImportHistory = async (limit: number = 50): Promise<ImportHistoryItem[]> => {
  const response = await apiClient.get<{ imports: ImportHistoryItem[] }>('/admin/communities/import-history', {
    params: { limit },
  });
  // The backend returns { code: 0, data: { imports: [...] } }. 
  // Interceptor unwraps to data: { imports: [...] }.
  // So response.data is { imports: [...] }.
  return response.data.imports || [];
};

// --- Task Ledger ---

export interface TaskLedgerItem {
  task_id: string;
  user_email: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  processing_seconds: number | null;
  confidence_score: number | null;
  analysis_version: number | null;
  posts_analyzed: number;
  cache_hit_rate: number;
  communities_count: number;
  reddit_api_calls: number;
  pain_points_count: number;
  competitors_count: number;
  opportunities_count: number;
}

export const getRecentTasks = async (params: { limit?: number; offset?: number }): Promise<{ items: TaskLedgerItem[]; total: number }> => {
  const response = await apiClient.get<{ items: TaskLedgerItem[]; total: number }>('/admin/tasks/recent', { params });
  return response.data;
};

export interface AdminTaskLedgerResponse {
  task: {
    id: string;
    user_id: string;
    status: string;
    product_description: string;
    created_at: string;
    completed_at: string | null;
    [key: string]: any;
  };
  analysis: {
    id: string;
    task_id: string;
    analysis_version: number;
    confidence_score: string | null;
    sources: {
      communities?: string[];
      posts_analyzed?: number;
      cache_hit_rate?: number;
      reddit_api_calls?: number;
      [key: string]: any;
    };
    created_at: string | null;
  } | null;
  facts_snapshot: {
    id: string;
    tier: string;
    status: string;
    quality: string;
    blocked_reason?: string;
    v2_package?: any;
    [key: string]: any;
  } | null;
}

export const getTaskLedger = async (taskId: string, includePackage: boolean = false): Promise<AdminTaskLedgerResponse> => {
  const response = await apiClient.get<AdminTaskLedgerResponse>(`/admin/tasks/${taskId}/ledger`, {
    params: { include_package: includePackage },
  });
  return response.data;
};