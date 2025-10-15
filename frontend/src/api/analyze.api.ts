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
  const response = await apiClient.post<AnalyzeResponse>('/api/analyze', request);
  return response.data;
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
  const response = await apiClient.get<TaskStatusResponse>(`/api/status/${taskId}`, {
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
  const response = await apiClient.get<ReportResponse>(`/api/report/${taskId}`);
  return response.data;
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
    
    // 检查任务是否完成
    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }
    
    // 等待下一次轮询
    await new Promise((resolve) => setTimeout(resolve, interval));
    attempts++;
  }
  
  throw new Error('任务轮询超时');
};

