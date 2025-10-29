/**
 * 质量指标类型定义
 *
 * 基于 Spec 007 User Story 2 (US2) - Task T027
 * 对应后端 backend/app/schemas/metrics.py
 * 最后更新: 2025-10-27
 */

/**
 * 每日质量指标
 */
export interface DailyMetrics {
  /** 指标日期 */
  date: string;

  /** 缓存命中率 (0.0-1.0) */
  cache_hit_rate: number;

  /** 24小时内有效帖子数 */
  valid_posts_24h: number;

  /** 总社区数 */
  total_communities: number;

  /** 重复率 (0.0-1.0) */
  duplicate_rate: number;

  /** Precision@50 指标 (0.0-1.0) */
  precision_at_50: number;

  /** 平均评分 (0.0-1.0) */
  avg_score: number;
}

/**
 * 每日质量指标列表响应
 */
export interface DailyMetricsListResponse {
  /** 指标列表 */
  metrics: DailyMetrics[];

  /** 总记录数 */
  total: number;
}

/**
 * 质量指标查询参数
 */
export interface MetricsQueryParams {
  /** 开始日期（YYYY-MM-DD 格式，默认为 7 天前） */
  start_date?: string;

  /** 结束日期（YYYY-MM-DD 格式，默认为今天） */
  end_date?: string;
}

/**
 * 图表数据点
 */
export interface ChartDataPoint {
  /** 日期（格式化后的字符串，如 "10/15"） */
  date: string;

  /** 缓存命中率（百分比，0-100） */
  cacheHitRate: number;

  /** 重复率（百分比，0-100） */
  duplicateRate: number;

  /** Precision@50（百分比，0-100） */
  precisionAt50: number;

  /** 有效帖子数 */
  validPosts: number;
}

/**
 * 将 DailyMetrics 转换为 ChartDataPoint
 */
export function toChartDataPoint(metric: DailyMetrics): ChartDataPoint {
  // 格式化日期为 MM/DD
  const dateObj = new Date(metric.date);
  const formattedDate = `${dateObj.getMonth() + 1}/${dateObj.getDate()}`;

  return {
    date: formattedDate,
    cacheHitRate: Math.round(metric.cache_hit_rate * 100),
    duplicateRate: Math.round(metric.duplicate_rate * 100),
    precisionAt50: Math.round(metric.precision_at_50 * 100),
    validPosts: metric.valid_posts_24h,
  };
}

/**
 * 质量指标阈值配置
 */
export interface MetricsThresholds {
  /** 缓存命中率最低阈值（百分比） */
  minCacheHitRate: number;

  /** 重复率最高阈值（百分比） */
  maxDuplicateRate: number;

  /** Precision@50 最低阈值（百分比） */
  minPrecisionAt50: number;

  /** 有效帖子数最低阈值 */
  minValidPosts: number;
}

/**
 * 默认质量指标阈值
 */
export const DEFAULT_METRICS_THRESHOLDS: MetricsThresholds = {
  minCacheHitRate: 60,
  maxDuplicateRate: 20,
  minPrecisionAt50: 60,
  minValidPosts: 1500,
};

/**
 * 检查指标是否异常
 */
export function isMetricAbnormal(
  metric: DailyMetrics,
  thresholds: MetricsThresholds = DEFAULT_METRICS_THRESHOLDS
): boolean {
  return (
    metric.cache_hit_rate * 100 < thresholds.minCacheHitRate ||
    metric.duplicate_rate * 100 > thresholds.maxDuplicateRate ||
    metric.precision_at_50 * 100 < thresholds.minPrecisionAt50 ||
    metric.valid_posts_24h < thresholds.minValidPosts
  );
}

