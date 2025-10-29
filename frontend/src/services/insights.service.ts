/**
 * Insights Service
 * 
 * 提供洞察卡片相关的 API 调用
 * 
 * 最后更新: 2025-10-22
 */

import {
  getInsightById as fetchInsightById,
  getInsights as fetchInsights,
  type GetInsightsParams,
} from '@/api/insights';
import type { InsightCard, InsightCardListResponse } from '@/types';

/**
 * 洞察卡片服务
 */
export const insightsService = {
  /**
   * 获取洞察卡片列表
   *
   * @param params 查询参数
   * @returns 洞察卡片列表响应
   */
  async getInsights(
    taskId: string,
    params: GetInsightsParams = {}
  ): Promise<InsightCardListResponse> {
    return fetchInsights(taskId, params);
  },

  /**
   * 获取单个洞察卡片详情
   *
   * @param insightId 洞察卡片 ID (UUID)
   * @returns 洞察卡片详情
   */
  async getInsightById(insightId: string): Promise<InsightCard> {
    return fetchInsightById(insightId);
  },
};
