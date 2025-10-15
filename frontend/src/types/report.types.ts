/**
 * 报告相关类型定义
 * 
 * 基于 PRD-02 API 设计规范 & Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-11 Day 5
 */

import type { Insights } from './analysis.types';
import type { RecoveryStrategy } from './api.types';

/**
 * 执行摘要接口
 */
export interface ExecutiveSummary {
  /** 分析的社区总数 */
  total_communities: number;
  
  /** 关键洞察数量 */
  key_insights: number;
  
  /** 最重要的机会描述 */
  top_opportunity: string;
}

/**
 * 降级质量信息接口（当使用恢复策略时）
 */
export interface FallbackQuality {
  /** 缓存覆盖率（0.0 到 1.0） */
  cache_coverage: number;
  
  /** 数据新鲜度（小时） */
  data_freshness_hours: number;
  
  /** 估计准确度（0.0 到 1.0） */
  estimated_accuracy: number;
}

/**
 * 报告元数据接口
 */
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

  /** 应用的恢复策略（可选） */
  recovery_applied?: RecoveryStrategy;

  /** 降级质量信息（仅在使用恢复策略时存在） */
  fallback_quality?: FallbackQuality;
}

/**
 * 市场情感分析接口
 */
export interface SentimentAnalysis {
  /** 正面情感百分比 */
  positive: number;

  /** 负面情感百分比 */
  negative: number;

  /** 中性情感百分比 */
  neutral: number;
}

/**
 * 热门社区接口
 */
export interface TopCommunity {
  /** 社区名称 */
  name: string;

  /** 提及次数 */
  mentions: number;

  /** 相关性百分比 */
  relevance: number;

  /** 社区分类 */
  category?: string;

  /** 每日帖子数 */
  daily_posts?: number;

  /** 平均评论长度 */
  avg_comment_length?: number;

  /** 是否来自缓存 */
  from_cache?: boolean;
}

/**
 * 概览数据接口
 */
export interface Overview {
  /** 市场情感分析 */
  sentiment: SentimentAnalysis;

  /** 热门社区列表（最多5个） */
  top_communities: TopCommunity[];
}

/**
 * 统计数据接口
 */
export interface Stats {
  /** 总提及数 */
  total_mentions: number;

  /** 正面提及数 */
  positive_mentions: number;

  /** 负面提及数 */
  negative_mentions: number;

  /** 中性提及数 */
  neutral_mentions: number;
}

/**
 * 报告响应接口
 */
export interface ReportResponse {
  /** 任务 ID (UUID) */
  task_id: string;

  /** 任务状态 */
  status: string;

  /** 报告生成时间 (ISO 8601) */
  generated_at: string;

  /** 产品描述 */
  product_description?: string;

  /** 报告内容 */
  report: {
    /** 执行摘要 */
    executive_summary: ExecutiveSummary;
    /** 核心洞察（痛点、竞品、机会） */
    pain_points: Insights['pain_points'];
    competitors: Insights['competitors'];
    opportunities: Insights['opportunities'];
  };

  /** 报告元数据 */
  metadata: ReportMetadata;

  /** 概览数据 */
  overview: Overview;

  /** 统计数据 */
  stats: Stats;
}
