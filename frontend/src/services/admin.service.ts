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
 * 社区决策请求
 */
export interface CommunityDecisionRequest {
  community: string;
  action: 'approve' | 'experiment' | 'pause' | 'blacklist';
  labels: string[];
  reason: string;
}

/**
 * 分析任务数据类型
 */
export interface AnalysisTaskData {
  task_id: string;
  started_at: string;
  duration_seconds: number;
  communities_count: number;
  a_score: number;
  must_pass: boolean;
  satisfaction?: boolean;
}

/**
 * 用户反馈汇总
 */
export interface FeedbackSummary {
  analysis_satisfaction_rate: number;
  top_fail_reasons: Array<{ reason: string; count: number }>;
  user_like_ratio: number;
  read_complete_rate: number;
  top_flagged_insight_types: Array<{ type: string; count: number }>;
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
   * 记录社区决策
   * POST /admin/decisions/community
   */
  recordCommunityDecision: async (
    decision: CommunityDecisionRequest
  ): Promise<{ event_id: string }> => {
    const response = await apiClient.post<{ data: { event_id: string } }>(
      '/admin/decisions/community',
      decision
    );
    return response.data.data;
  },

  /**
   * 生成配置补丁
   * GET /admin/config/patch
   */
  generatePatch: async (since?: string): Promise<string> => {
    const response = await apiClient.get<string>('/admin/config/patch', {
      params: { since },
      headers: { Accept: 'text/yaml' },
    });
    return response.data;
  },

  /**
   * 获取分析任务列表
   * GET /admin/analysis/tasks
   */
  getAnalysisTasks: async (params?: {
    page?: number;
    page_size?: number;
  }): Promise<{ items: AnalysisTaskData[]; total: number }> => {
    const response = await apiClient.get<{
      data: { items: AnalysisTaskData[]; total: number };
    }>('/admin/analysis/tasks', { params });
    return response.data.data;
  },

  /**
   * 记录分析反馈
   * POST /admin/feedback/analysis
   */
  recordAnalysisFeedback: async (feedback: {
    task_id: string;
    is_satisfied: boolean;
    reasons: string[];
    notes?: string;
  }): Promise<{ event_id: string }> => {
    const response = await apiClient.post<{ data: { event_id: string } }>(
      '/admin/feedback/analysis',
      feedback
    );
    return response.data.data;
  },

  /**
   * 获取反馈汇总
   * GET /admin/feedback/summary
   */
  getFeedbackSummary: async (days: number = 30): Promise<FeedbackSummary> => {
    const response = await apiClient.get<{ data: FeedbackSummary }>(
      '/admin/feedback/summary',
      { params: { days } }
    );
    return response.data.data;
  },

  /**
   * 获取系统状态
   * GET /admin/system/status
   */
  getSystemStatus: async (): Promise<string> => {
    const response = await apiClient.get<{ data: { status: string } }>(
      '/admin/system/status'
    );
    return response.data.data.status;
  },
};

