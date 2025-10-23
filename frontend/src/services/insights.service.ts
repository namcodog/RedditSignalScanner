/**
 * Insights Service
 * 
 * 提供洞察卡片相关的 API 调用
 * 
 * 最后更新: 2025-10-22
 */

import { apiClient } from '@/api/client';
import type { InsightCard, InsightCardListResponse } from '@/types';

/**
 * 获取洞察卡片列表查询参数
 */
export interface GetInsightsParams {
  /** 任务 ID (UUID) */
  task_id: string;
  
  /** 最小置信度 (0.0-1.0) */
  min_confidence?: number;
  
  /** 子版块过滤 */
  subreddit?: string;
  
  /** 跳过的记录数 */
  skip?: number;
  
  /** 每页记录数 */
  limit?: number;
}

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
  async getInsights(params: GetInsightsParams): Promise<InsightCardListResponse> {
    const response = await apiClient.get<InsightCardListResponse>('/insights', {
      params,
    });
    return response.data;
  },

  /**
   * 获取单个洞察卡片详情
   *
   * @param insightId 洞察卡片 ID (UUID)
   * @returns 洞察卡片详情
   */
  async getInsightById(insightId: string): Promise<InsightCard> {
    const response = await apiClient.get<InsightCard>(`/insights/${insightId}`);
    return response.data;
  },
};

