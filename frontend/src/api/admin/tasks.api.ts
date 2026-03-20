import { apiClient } from '../client';

export interface ActiveUserItem {
  user_id: string;
  email: string;
  tasks_last_7_days: number;
  last_task_at: string | null;
}

export const getActiveUsers = async (limit?: number): Promise<{ items: ActiveUserItem[]; total: number }> => {
  const response = await apiClient.get<{ items: ActiveUserItem[]; total: number }>('/admin/users/active', {
    params: { limit },
  });
  return response.data;
};

export interface TaskQueueStats {
  [key: string]: any;
}

export const getTaskQueueStats = async (): Promise<TaskQueueStats> => {
  const response = await apiClient.get<TaskQueueStats>('/tasks/stats');
  return response.data;
};

export interface QualityMetrics {
  date: string;
  collection_success_rate: number;
  deduplication_rate: number;
  processing_time_p50: number;
  processing_time_p95: number;
}

export const getQualityMetrics = async (params?: {
  start_date?: string;
  end_date?: string;
}): Promise<QualityMetrics[]> => {
  const response = await apiClient.get<QualityMetrics[]>('/metrics', { params });
  return response.data;
};

export const getBetaFeedbackList = async (): Promise<any> => {
  const response = await apiClient.get<any>('/admin/beta/feedback');
  return response.data;
};

export const getRuntimeDiagnostics = async (): Promise<any> => {
  const response = await apiClient.get<any>('/diag/runtime');
  return response.data;
};

export const getTasksDiagnostics = async (): Promise<any> => {
  const response = await apiClient.get<any>('/tasks/diag');
  return response.data;
};

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

export const getRecentTasks = async (params: {
  limit?: number;
  offset?: number;
}): Promise<{ items: TaskLedgerItem[]; total: number }> => {
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

export const getTaskLedger = async (
  taskId: string,
  includePackage: boolean = false,
): Promise<AdminTaskLedgerResponse> => {
  const response = await apiClient.get<AdminTaskLedgerResponse>(`/admin/tasks/${taskId}/ledger`, {
    params: { include_package: includePackage },
  });
  return response.data;
};
