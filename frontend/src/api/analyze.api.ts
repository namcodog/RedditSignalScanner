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
import { reportResponseSchema } from '@/types';
import {
  REPORT_CACHE_TTL_MS_DEFAULT,
  REPORT_POLL_INTERVAL_MS,
  REPORT_MAX_POLL_ATTEMPTS,
} from '@/config/report';

interface ReportCacheEntry {
  data: ReportResponse;
  expires: number;
}

const REPORT_CACHE_TTL_MS = (() => {
  const raw = Number((import.meta as any)?.env?.VITE_REPORT_CACHE_TTL_MS);
  return Number.isFinite(raw) && raw > 0 ? raw : REPORT_CACHE_TTL_MS_DEFAULT;
})();
const REPORT_CACHE_STORAGE_PREFIX = 'report_cache_';

const reportCache = new Map<string, ReportCacheEntry>();
const pendingRequests = new Map<string, Promise<ReportResponse>>();

const safeGetStorage = (): Storage | null => {
  try {
    if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
      return null;
    }
    return window.localStorage;
  } catch {
    return null;
  }
};

const getCacheKey = (taskId: string): string =>
  `${REPORT_CACHE_STORAGE_PREFIX}${taskId}`;

const readCacheFromStorage = (taskId: string): ReportCacheEntry | null => {
  const storage = safeGetStorage();
  if (!storage) return null;

  const key = getCacheKey(taskId);
  const raw = storage.getItem(key);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as ReportCacheEntry | null;
    if (!parsed || typeof parsed.expires !== 'number' || !parsed.data) {
      storage.removeItem(key);
      return null;
    }
    if (parsed.expires <= Date.now()) {
      storage.removeItem(key);
      return null;
    }
    return parsed;
  } catch {
    storage.removeItem(key);
    return null;
  }
};

const writeCacheToStorage = (taskId: string, entry: ReportCacheEntry): void => {
  const storage = safeGetStorage();
  if (!storage) return;

  try {
    storage.setItem(getCacheKey(taskId), JSON.stringify(entry));
  } catch {
    // 忽略 localStorage 写入异常（如存储空间不足）
  }
};

const removeCacheFromStorage = (taskId: string): void => {
  const storage = safeGetStorage();
  if (!storage) return;

  try {
    storage.removeItem(getCacheKey(taskId));
  } catch {
    // 忽略删除异常
  }
};

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
export const getAnalysisReport = (taskId: string): Promise<ReportResponse> => {
  const now = Date.now();
  const cached = reportCache.get(taskId);

  if (cached) {
    if (cached.expires > now) {
      return Promise.resolve(cached.data);
    }
    reportCache.delete(taskId);
    removeCacheFromStorage(taskId);
  }

  const stored = readCacheFromStorage(taskId);
  if (stored) {
    // Check if the stored cache has expired
    if (stored.expires > now) {
      reportCache.set(taskId, stored);
      return Promise.resolve(stored.data);
    }
    // Cache has expired, remove it from storage
    removeCacheFromStorage(taskId);
  }

  const ongoing = pendingRequests.get(taskId);
  if (ongoing) {
    return ongoing;
  }

  const request = (async () => {
  const response = await apiClient.get(`/report/${taskId}`);
  let data: ReportResponse;
  try {
    data = reportResponseSchema.parse(response.data);
  } catch (error) {
    console.error('[Report] Schema validation failed:', error);
    throw new Error('报告数据格式异常，请稍后重试');
  }
    const entry: ReportCacheEntry = {
      data,
      expires: Date.now() + REPORT_CACHE_TTL_MS,
    };
    reportCache.set(taskId, entry);
    writeCacheToStorage(taskId, entry);
    return data;
  })();

  pendingRequests.set(taskId, request);
  void request.finally(() => {
    pendingRequests.delete(taskId);
  });

  return request;
};

// 完整/Top 社区导出（结构化 JSON）
export interface CommunityExportItem {
  name: string;
  mentions: number;
  relevance?: number | null;
  category?: string | null;
  categories?: string[];
  daily_posts?: number | null;
  avg_comment_length?: number | null;
  from_cache?: boolean | null;
  cache_hit_rate?: number | null;
  members?: number | null;
  priority?: string | null;
  tier?: string | null;
  is_blacklisted?: boolean | null;
  blacklist_reason?: string | null;
  is_active?: boolean | null;
  crawl_frequency_hours?: number | null;
  crawl_priority?: number | null;
  last_crawled_at?: string | null;
  posts_cached?: number | null;
  hit_count?: number | null;
  empty_hit?: number | null;
  failure_hit?: number | null;
  success_hit?: number | null;
}

export interface CommunityExportResponse {
  task_id: string;
  scope: 'top' | 'all';
  seed_source?: string;
  top_n?: number;
  total_communities?: number;
  items: CommunityExportItem[];
}

export const getReportCommunities = async (
  taskId: string,
  scope: 'top' | 'all' = 'all'
): Promise<CommunityExportResponse> => {
  const response = await apiClient.get(`/report/${taskId}/communities`, {
    params: { scope },
  });
  // 不做严格 zod 校验，后端已约束；仅保证 items 是数组
  const data = response.data as CommunityExportResponse;
  if (!data || !Array.isArray(data.items)) {
    throw new Error('社区导出数据格式异常');
  }
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
  interval = REPORT_POLL_INTERVAL_MS,
  maxAttempts = REPORT_MAX_POLL_ATTEMPTS,
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
