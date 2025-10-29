/**
 * 洞察卡片 API 客户端
 *
 * 对应 Spec 007 Phase 3 (US1) 的后端接口：
 * - GET /api/insights/{task_id}
 * - GET /api/insights/card/{insight_id}
 */

import { apiClient } from './client';
import type {
  InsightCard,
  InsightCardListResponse,
} from '@/types/insight.types';

/**
 * 洞察卡片查询参数
 */
export interface GetInsightsParams {
  /** 最小置信度 (0.0-1.0) */
  min_confidence?: number;

  /** 子版块过滤，区分大小写 */
  subreddit?: string;

  /** 跳过的记录数 */
  offset?: number;

  /** 返回数量 */
  limit?: number;
}

/**
 * 获取指定任务的洞察卡片列表
 */
export async function getInsights(
  taskId: string,
  params: GetInsightsParams = {}
): Promise<InsightCardListResponse> {
  const response = await apiClient.get<InsightCardListResponse>(
    `/insights/${taskId}`,
    { params }
  );
  return response.data;
}

/**
 * 获取单个洞察卡片详情
 */
export async function getInsightById(
  insightId: string
): Promise<InsightCard> {
  const response = await apiClient.get<InsightCard>(
    `/insights/card/${insightId}`
  );
  return response.data;
}

export const insightsApi = {
  getInsights,
  getInsightById,
};

export default insightsApi;
