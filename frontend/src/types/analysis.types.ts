/**
 * 分析结果相关类型定义
 * 
 * 基于 PRD-02 API 设计规范 & Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-11 Day 5
 */

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
  
  /** 帖子内容摘要 */
  content: string;
  
  /** 点赞数 */
  upvotes: number;
  
  /** Reddit 帖子链接（可选） */
  url?: string;
  
  /** 作者用户名（可选） */
  author?: string;
  
  /** 帖子创建时间 (ISO 8601)（可选） */
  created_at?: string;
}

/**
 * 痛点接口
 */
export interface PainPoint {
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
  sentiment: Sentiment;

  /** 优势列表（建议最多 10 项） */
  strengths: string[];

  /** 劣势列表（建议最多 10 项） */
  weaknesses: string[];

  /** 市场份额百分比（0-100） */
  market_share?: number;
}

/**
 * 机会接口
 */
export interface Opportunity {
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
 * 核心洞察接口
 */
export interface Insights {
  /** 痛点列表 */
  pain_points: PainPoint[];
  
  /** 竞品列表 */
  competitors: Competitor[];
  
  /** 机会列表 */
  opportunities: Opportunity[];
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
  analysis_duration_seconds: number;

  /** Reddit API 调用次数 */
  reddit_api_calls: number;

  /** 产品描述 */
  product_description?: string;
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
