/**
 * Admin Dashboard Service
 *
 * 基于 PRD-07 Admin后台设计
 * 提供社区验收、算法验收、用户反馈等功能的API调用
 *
 * 最后更新: 2025-10-15 Day 10
 */

import { apiClient } from '@/api/client';

/**
 * 社区数据类型
 */
export interface CommunityData {
  community: string;
  hit_7d: number;
  last_crawled_at: string;
  dup_ratio: number;
  spam_ratio: number;
  topic_score: number;
  c_score: number;
  status_color: 'green' | 'yellow' | 'red';
  labels: string[];
  evidence_samples?: string[];
}

/**
 * 社区列表响应
 */
export interface CommunitySummaryResponse {
  items: CommunityData[];
  total: number;
}

/**
 * 质量指标数据类型
 */
export interface QualityMetrics {
  date: string;
  collection_success_rate: number;
  deduplication_rate: number;
  processing_time_p50: number;
  processing_time_p95: number;
}

export interface CommunityImportSummary {
  total: number;
  valid: number;
  invalid: number;
  duplicates: number;
  imported: number;
}

export interface CommunityImportError {
  row: number;
  field: string;
  value: string | null;
  error: string;
}

export interface CommunityImportResult {
  status: 'success' | 'error' | 'validated';
  summary: CommunityImportSummary;
  errors?: CommunityImportError[];
  communities?: Array<{
    name: string;
    tier: string;
    status: string;
  }>;
}

export interface CommunityImportHistoryEntry {
  id: number;
  filename: string;
  uploaded_by: string;
  uploaded_at: string;
  dry_run: boolean;
  status: string;
  summary: CommunityImportSummary;
}

export interface BetaFeedbackItem {
  id: string;
  task_id: string;
  user_id: string;
  satisfaction: string;
  missing_communities: string[] | null;
  comments: string | null;
  created_at: string;
}

export interface BetaFeedbackResponse {
  items: BetaFeedbackItem[];
  total: number;
}

/**
 * Admin Service
 */
export const adminService = {
  /**
   * 获取社区列表
   * GET /admin/communities/summary
   */
  getCommunities: async (params?: {
    q?: string;
    status?: 'green' | 'yellow' | 'red';
    tag?: string;
    sort?: 'cscore_desc' | 'hit_desc';
    page?: number;
    page_size?: number;
  }): Promise<CommunitySummaryResponse> => {
    const response = await apiClient.get<{ data: CommunitySummaryResponse }>(
      '/admin/communities/summary',
      { params }
    );
    return response.data.data;
  },

  /**
   * 获取分析任务列表
   * GET /admin/tasks/recent
   */
  getAnalysisTasks: async (params?: {
    limit?: number;
  }): Promise<{ items: any[]; total: number }> => {
    const response = await apiClient.get<{
      data: { items: any[]; total: number };
    }>('/admin/tasks/recent', { params });
    return response.data.data;
  },

  /**
   * 获取质量指标
   * GET /metrics
   */
  getQualityMetrics: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<QualityMetrics[]> => {
    const response = await apiClient.get<QualityMetrics[]>('/metrics', {
      params,
    });
    return response.data;
  },

  /**
   * 获取社区池列表
   * GET /admin/communities/pool
   */
  getCommunityPool: async (params?: {
    page?: number;
    page_size?: number;
    tier?: number;
    is_active?: boolean;
  }): Promise<{ items: CommunityData[]; total: number }> => {
    const response = await apiClient.get<{ data: { items: CommunityData[]; total: number } }>(
      '/admin/communities/pool',
      { params }
    );
    return response.data.data;
  },

  /**
   * 获取待审核社区列表（智能发现）
   * GET /admin/communities/discovered
   */
  getDiscoveredCommunities: async (params?: {
    page?: number;
    page_size?: number;
    min_score?: number;
  }): Promise<{ items: Array<{ name: string; score?: number; tier?: number; labels?: string[] }>; total: number }> => {
    const response = await apiClient.get<{ data: { items: Array<{ name: string; score?: number; tier?: number; labels?: string[] }>; total: number } }>(
      '/admin/communities/discovered',
      { params }
    );
    return response.data.data;
  },

  /**
   * 批准社区
   * POST /admin/communities/approve
   */
  approveCommunity: async (payload: { community_name: string; tier?: number; categories?: string[] }): Promise<{ event_id: string }> => {
    const response = await apiClient.post<{ data: { event_id: string } }>(
      '/admin/communities/approve',
      payload
    );
    return response.data.data;
  },

  /**
   * 拒绝社区
   * POST /admin/communities/reject
   */
  rejectCommunity: async (payload: { community_name: string; reason: string }): Promise<{ event_id: string }> => {
    const response = await apiClient.post<{ data: { event_id: string } }>(
      '/admin/communities/reject',
      payload
    );
    return response.data.data;
  },

  /**
   * 获取仪表盘统计
   * GET /admin/dashboard/stats
   */
  getDashboardStats: async (): Promise<{ total_users: number; total_tasks: number; total_communities: number; cache_hit_rate: number }> => {
    const response = await apiClient.get<{ data: { total_users: number; total_tasks: number; total_communities: number; cache_hit_rate: number } }>(
      '/admin/dashboard/stats'
    );
    return response.data.data;
  },

  /**
   * 禁用社区
   * DELETE /admin/communities/{name}
   */
  disableCommunity: async (name: string): Promise<{ disabled: string }> => {
    const response = await apiClient.delete<{ data: { disabled: string } }>(
      `/admin/communities/${encodeURIComponent(name)}`
    );
    return response.data.data;
  },

  /**
   * 获取活跃用户
   * GET /admin/users/active
   */
  getActiveUsers: async (limit?: number): Promise<{ items: Array<{ user_id: string; email: string; tasks_last_7_days: number; last_task_at: string }>; total: number }> => {
    const response = await apiClient.get<{ data: { items: Array<{ user_id: string; email: string; tasks_last_7_days: number; last_task_at: string }>; total: number } }>(
      '/admin/users/active',
      { params: { limit } }
    );
    return response.data.data;
  },

  /**
   * 获取任务队列统计
   * GET /tasks/stats
   */
  getTaskQueueStats: async (): Promise<{ active_workers: number; active_tasks: number; reserved_tasks: number; scheduled_tasks: number; total_tasks: number }> => {
    const response = await apiClient.get<{ active_workers: number; active_tasks: number; reserved_tasks: number; scheduled_tasks: number; total_tasks: number }>(
      '/tasks/stats'
    );
    return response.data;
  },

  /**
   * 下载社区导入模板
   * GET /admin/communities/template
   */
  downloadCommunityTemplate: async (): Promise<Blob> => {
    const response = await apiClient.get<Blob>('/admin/communities/template', {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * 上传社区导入文件
   * POST /admin/communities/import
   */
  uploadCommunityImport: async (
    file: File,
    options: { dryRun?: boolean; onProgress?: (percent: number) => void } = {}
  ): Promise<CommunityImportResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<{ data: CommunityImportResult }>(
      '/admin/communities/import',
      formData,
      {
        params: { dry_run: options.dryRun ?? false },
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (options.onProgress && event.total) {
            const percent = Math.round((event.loaded / event.total) * 100);
            options.onProgress(percent);
          }
        },
      }
    );
    return response.data.data;
  },

  /**
   * 获取社区导入历史
   * GET /admin/communities/import-history
   */
  getCommunityImportHistory: async (): Promise<CommunityImportHistoryEntry[]> => {
    const response = await apiClient.get<{ data: { imports: CommunityImportHistoryEntry[] } }>(
      '/admin/communities/import-history'
    );
    return response.data.data.imports;
  },

  /**
   * 获取用户反馈列表
   * GET /admin/beta/feedback
   */
  getBetaFeedbackList: async (): Promise<BetaFeedbackResponse> => {
    const response = await apiClient.get<{ data: BetaFeedbackResponse }>(
      '/admin/beta/feedback'
    );
    return response.data.data;
  },

  /**
   * P2: 获取运行时诊断信息
   * GET /diag/runtime
   */
  getRuntimeDiagnostics: async (): Promise<{
    timestamp: string;
    python: {
      version: string;
      executable: string;
      platform: string;
      architecture: string;
    };
    system: {
      cpu_percent: number;
      cpu_count: number;
      memory_total_mb: number;
      memory_available_mb: number;
      memory_percent: number;
      disk_usage_percent: number;
    };
    process: {
      pid: number;
      memory_rss_mb: number;
      memory_vms_mb: number;
      cpu_percent: number;
      num_threads: number;
      create_time: string;
    };
    database: {
      connected: boolean;
      error: string | null;
    };
  }> => {
    const response = await apiClient.get<{
      timestamp: string;
      python: {
        version: string;
        executable: string;
        platform: string;
        architecture: string;
      };
      system: {
        cpu_percent: number;
        cpu_count: number;
        memory_total_mb: number;
        memory_available_mb: number;
        memory_percent: number;
        disk_usage_percent: number;
      };
      process: {
        pid: number;
        memory_rss_mb: number;
        memory_vms_mb: number;
        cpu_percent: number;
        num_threads: number;
        create_time: string;
      };
      database: {
        connected: boolean;
        error: string | null;
      };
    }>('/diag/runtime');
    return response.data;
  },

  /**
   * P2: 获取任务诊断信息
   * GET /tasks/diag
   */
  getTasksDiagnostics: async (): Promise<{
    has_reddit_client: boolean;
    environment: string;
  }> => {
    const response = await apiClient.get<{
      has_reddit_client: boolean;
      environment: string;
    }>('/tasks/diag');
    return response.data;
  }
};
