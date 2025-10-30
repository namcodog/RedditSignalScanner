/**
 * 报告元数据（Report Metadata）相关类型
 */

export interface FallbackQuality {
  /** 缓存覆盖率（0.0 到 1.0） */
  cache_coverage: number;
  /** 数据新鲜度（小时） */
  data_freshness_hours: number;
  /** 估计准确度（0.0 到 1.0） */
  estimated_accuracy: number;
}

export interface ReportMetadata {
  /** 分析引擎版本 */
  analysis_version: string;
  /** 置信度分数（0.00 到 1.00） */
  confidence_score: number;
  /** 处理耗时（秒） */
  processing_time_seconds: number;
  /** 缓存命中率（0.0 到 1.0） */
  cache_hit_rate: number;
  /** 总提及数 */
  total_mentions: number;
  /** 应用的恢复策略（可选，字符串标识） */
  recovery_applied?: string | null | undefined;
  /** 降级质量信息（仅在使用恢复策略时存在） */
  fallback_quality?: FallbackQuality | null | undefined;
}
