/**
 * 质量指标 API 服务
 *
 * 基于 Spec 007 User Story 2 (US2) - Task T028
 * 提供每日质量指标查询接口
 * 最后更新: 2025-10-27
 */

import { apiClient } from './client';
import type {
  DailyMetricsListResponse,
  MetricsQueryParams,
} from '@/types/metrics';

/**
 * 获取每日质量指标
 *
 * @param params - 查询参数（可选）
 * @returns 每日质量指标列表
 *
 * @example
 * ```ts
 * // 获取最近 7 天的指标
 * const metrics = await getDailyMetrics();
 *
 * // 获取指定日期范围的指标
 * const metrics = await getDailyMetrics({
 *   start_date: '2025-10-15',
 *   end_date: '2025-10-21',
 * });
 * ```
 */
export async function getDailyMetrics(
  params?: MetricsQueryParams
): Promise<DailyMetricsListResponse> {
  const query: Record<string, string> = {};
  if (params?.start_date) {
    query['start_date'] = params.start_date;
  }
  if (params?.end_date) {
    query['end_date'] = params.end_date;
  }

  const response = await apiClient.get<DailyMetricsListResponse>(
    '/api/metrics/daily',
    { params: query }
  );
  return response.data;
}

/**
 * 获取最近 N 天的质量指标
 *
 * @param days - 天数（默认 7 天）
 * @returns 每日质量指标列表
 *
 * @example
 * ```ts
 * // 获取最近 30 天的指标
 * const metrics = await getRecentMetrics(30);
 * ```
 */
export async function getRecentMetrics(
  days: number = 7
): Promise<DailyMetricsListResponse> {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);

  const startDateStr = startDate.toISOString().slice(0, 10);
  const endDateStr = endDate.toISOString().slice(0, 10);

  const query = {
    start_date: startDateStr,
    end_date: endDateStr,
  } satisfies MetricsQueryParams;

  return getDailyMetrics(query);
}
