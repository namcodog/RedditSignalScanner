/**
 * 分析结果相关类型定义
 * 
 * 基于 PRD-02 API 设计规范 & Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-11 Day 5
 */

import type { EntitySummary } from './report';

/**
 * 情感倾向枚举
 */
export enum Sentiment {
  /** 正面 */
  POSITIVE = 'positive',
  /** 负面 */
  NEGATIVE = 'negative',
  /** 混合 */
  MIXED = 'mixed',
}

/**
 * 示例帖子接口
 */
export interface ExamplePost {
  /** 社区名称（如 "r/productivity"） */
  community: string;

  /** 帖子标题（可选） */
  title?: string;

  /** 帖子内容摘要（允许 null） */
  content?: string | null | undefined;

  /** 点赞数（允许 null） */
  upvotes?: number | null | undefined;

  /** Reddit 帖子链接（可选，允许 null） */
  url?: string | null | undefined;

  /** 作者用户名（可选，允许 null） */
  author?: string | null | undefined;

  /** 帖子创建时间 (ISO 8601)（可选，允许 null） */
  created_at?: string | null | undefined;

  /** 帖子永久链接（可选，允许 null） */
  permalink?: string | null | undefined;
}

/**
 * 痛点接口
 */
export interface PainPoint {
  /** 痛点文本摘要 */
  text?: string;

  /** 痛点描述 */
  description: string;

  /** 出现频率 */
  frequency: number;

  /** 情感分数（-1.0 到 1.0） */
  sentiment_score: number;

  /** 严重程度 */
  severity: 'low' | 'medium' | 'high';

  /** 示例帖子列表 */
  example_posts: ExamplePost[];

  /** 用户示例引用（3条） */
  user_examples: string[];
}

/**
 * 竞品接口
 */
export interface Competitor {
  /** 竞品名称 */
  name: string;

  /** 提及次数 */
  mentions: number;

  /** 情感倾向 */
  sentiment: string;

  /** 优势列表（建议最多 10 项） */
  strengths: string[];

  /** 劣势列表（建议最多 10 项） */
  weaknesses: string[];

  /** 市场份额百分比（0-100） */
  market_share?: number | null | undefined;
}

/**
 * 机会接口
 */
export interface Opportunity {
  /** 机会标题 */
  title?: string;

  /** 机会文本摘要 */
  text?: string;

  /** 机会描述 */
  description: string;

  /** 相关性分数（0.0 到 1.0） */
  relevance_score: number;

  /** 潜在用户描述 */
  potential_users: string;

  /** 关键洞察列表（4条） */
  key_insights: string[];
}

/**
 * 社区来源明细接口
 */
export interface CommunitySourceDetail {
  /** 社区名称 */
  name: string;

  /** 社区分类 */
  categories: string[];

  /** 提及次数 */
  mentions: number;

  /** 日均帖子数 */
  daily_posts: number;

  /** 平均评论长度 */
  avg_comment_length: number;

  /** 缓存命中率（0.0 到 1.0） */
  cache_hit_rate: number;

  /** 是否来自缓存 */
  from_cache: boolean;
}

/**
 * 核心洞察接口
 */
export interface Insights {
  /** 痛点列表 */
  pain_points: PainPoint[];
  
  /** 竞品列表 */
  competitors: Competitor[];
  
  /** 机会列表 */
  opportunities: Opportunity[];

  /** 实体匹配摘要 */
  entity_summary?: EntitySummary;
}

/**
 * 数据溯源接口
 */
export interface Sources {
  /** 分析的社区列表 */
  communities: string[];

  /** 分析的帖子数量 */
  posts_analyzed: number;

  /** 缓存命中率（0.0 到 1.0） */
  cache_hit_rate: number;

  /** 分析耗时（秒） */
  analysis_duration_seconds?: number | null | undefined;

  /** Reddit API 调用次数 */
  reddit_api_calls?: number | null | undefined;

  /** 产品描述 */
  product_description?: string | null | undefined;

  /** PS 比率 */
  ps_ratio?: number | null | undefined;

  /** 混合帖子使用数 */
  hybrid_posts_used?: number | null | undefined;

  /** 采集警告 */
  collection_warnings?: string[] | null | undefined;

  /** 社区来源明细 */
  communities_detail?: CommunitySourceDetail[] | null | undefined;

  /** 恢复策略 */
  recovery_strategy?: string | null | undefined;

  /** 降级质量 */
  fallback_quality?: Record<string, unknown> | null | undefined;

  /** 去重统计 */
  dedup_stats?: Record<string, unknown> | null | undefined;

  /** 重复摘要 */
  duplicates_summary?: Record<string, unknown>[] | null | undefined;

  /** 社区种子来源 */
  seed_source?: string | null | undefined;

  /** 数据源类型 */
  data_source?: string | null | undefined;

  /** 报告质量分层 */
  report_tier?: string | null | undefined;

  /** 分析阻塞原因 */
  analysis_blocked?: string | null | undefined;

  /** facts v2 质量详情 */
  facts_v2_quality?: Record<string, unknown> | null | undefined;

  /** 趋势来源 */
  trend_source?: string[] | null | undefined;

  /** 趋势是否降级 */
  trend_degraded?: boolean | null | undefined;

  /** facts 切片 */
  facts_slice?: Record<string, unknown> | null | undefined;

  /** 结构化报告 */
  report_structured?: Record<string, unknown> | null | undefined;

  /** 结构化 LLM 状态 */
  structured_llm_status?: string | null | undefined;

  /** 结构化 LLM 原因 */
  structured_llm_reason?: string | null | undefined;

  /** 知识图谱 */
  knowledge_graph?: Record<string, unknown> | null | undefined;

  /** 是否使用 LLM */
  llm_used?: boolean | null | undefined;

  /** LLM 模型 */
  llm_model?: string | null | undefined;

  /** LLM 轮次 */
  llm_rounds?: number | null | undefined;
}

/**
 * 分析结果接口
 */
export interface Analysis {
  /** 分析 ID (UUID) */
  id: string;
  
  /** 任务 ID (UUID) */
  task_id: string;
  
  /** 核心洞察 */
  insights: Insights;
  
  /** 数据溯源 */
  sources: Sources;
  
  /** 置信度分数（0.00 到 1.00） */
  confidence_score: number;
  
  /** 分析引擎版本（如 "1.0"） */
  analysis_version: string;
  
  /** 分析创建时间 (ISO 8601) */
  created_at: string;
}
