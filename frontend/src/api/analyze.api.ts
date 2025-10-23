/**
 * 分析任务 API 服务
 *
 * 基于 PRD-02 API 设计规范
 * 最后更新: 2025-10-10 Day 2
 */

import { apiClient } from './client';
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  TaskStatusResponse,
  ReportResponse,
} from '@/types';

// 简单的报告缓存（P1：添加缓存机制）
const REPORT_CACHE_TTL_MS = Number((import.meta as any)?.env?.VITE_REPORT_CACHE_TTL_MS) || 60_000;
const reportCache = new Map<string, { data: ReportResponse; expires: number }>();

/**
 * 用户反馈请求
 */
export interface BetaFeedbackRequest {
  task_id: string;
  satisfaction: number; // 1-5
  missing_communities?: string[];
  comments?: string;
}

/**
 * 用户反馈响应
 */
export interface BetaFeedbackResponse {
  id: string;
  task_id: string;
  user_id: string;
  satisfaction: number;
  missing_communities: string[];
  comments: string;
  created_at: string;
  updated_at: string;
}

/**
 * 创建分析任务
 *
 * POST /api/analyze
 *
 * @param request 分析请求
 * @returns 任务创建响应
 */
export const createAnalyzeTask = async (
  request: AnalyzeRequest
): Promise<AnalyzeResponse> => {
  try {
    const timeout = Number((import.meta as any)?.env?.VITE_ANALYZE_TIMEOUT) || 20_000;
    const response = await apiClient.post<AnalyzeResponse>('/analyze', request, { timeout });
    return response.data;
  } catch (error: any) {
    // Axios timeout code
    if (error && (error.code === 'ECONNABORTED' || /timeout/i.test(String(error.message)))) {
      throw new Error('请求超时，请稍后重试');
    }
    throw error;
  }
};

/**
 * 查询任务状态（轮询方式，作为 SSE 的 fallback）
 *
 * GET /api/status/{task_id}
 *
 * @param taskId 任务 ID
 * @returns 任务状态响应
 */
export const getTaskStatus = async (
  taskId: string
): Promise<TaskStatusResponse> => {
  const response = await apiClient.get<TaskStatusResponse>(`/status/${taskId}`, {
    headers: {
      'X-Fallback-Mode': 'polling',
    },
  });
  return response.data;
};

/**
 * 获取分析报告
 *
 * GET /api/report/{task_id}
 *
 * @param taskId 任务 ID
 * @returns 分析报告
 */
export const getAnalysisReport = async (
  taskId: string
): Promise<ReportResponse> => {
  const now = Date.now();
  const cached = reportCache.get(taskId);
  if (cached && cached.expires > now) {
    return cached.data;
  }
  const response = await apiClient.get<ReportResponse>(`/report/${taskId}`);
  const data = response.data;
  reportCache.set(taskId, { data, expires: now + REPORT_CACHE_TTL_MS });
  return data;
};

/**
 * 轮询任务状态直到完成
 * 
 * @param taskId 任务 ID
 * @param interval 轮询间隔（毫秒），默认 2000ms
 * @param maxAttempts 最大轮询次数，默认 150（5 分钟）
 * @param onProgress 进度回调
 * @returns 最终任务状态
 */
export const pollTaskUntilComplete = async (
  taskId: string,
  interval = 2000,
  maxAttempts = 150,
  onProgress?: (status: TaskStatusResponse) => void
): Promise<TaskStatusResponse> => {
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    const status = await getTaskStatus(taskId);
    
    // 调用进度回调
    if (onProgress !== undefined) {
      onProgress(status);
    }

    const isTerminal = status.status === 'completed' || status.status === 'failed';
    if (isTerminal) {
      return status;
    }

    await new Promise((resolve) => setTimeout(resolve, interval));
    attempts++;
  }

  throw new Error('任务轮询超时');
};

/**
 * 提交用户反馈
 *
 * POST /api/beta/feedback
 *
 * @param feedback 反馈数据
 * @returns 反馈响应
 */
export const submitBetaFeedback = async (
  feedback: BetaFeedbackRequest
): Promise<BetaFeedbackResponse> => {
  const response = await apiClient.post<{ data: BetaFeedbackResponse }>(
    '/beta/feedback',
    feedback
  );
  return response.data.data;
};
