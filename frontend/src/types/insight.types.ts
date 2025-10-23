/**
 * 洞察卡片相关类型定义
 * 
 * 基于 backend/app/schemas/insights.py
 */

/**
 * 证据项接口
 */
export interface Evidence {
  /** 证据 ID (UUID) */
  id: string;
  
  /** 原帖 URL */
  post_url: string;
  
  /** 摘录内容 */
  excerpt: string;
  
  /** 帖子时间戳 (ISO 8601) */
  timestamp: string;
  
  /** 子版块名称 */
  subreddit: string;
  
  /** 证据分数 (0.0-1.0) */
  score: number;
}

/**
 * 洞察卡片接口
 */
export interface InsightCard {
  /** 洞察卡片 ID (UUID) */
  id: string;
  
  /** 任务 ID (UUID) */
  task_id: string;
  
  /** 洞察标题 */
  title: string;
  
  /** 洞察摘要 */
  summary: string;
  
  /** 置信度 (0.0-1.0) */
  confidence: number;
  
  /** 时间窗口（天数） */
  time_window_days: number;
  
  /** 相关子版块列表 */
  subreddits: string[];
  
  /** 证据列表 */
  evidences: Evidence[];
  
  /** 创建时间 (ISO 8601) */
  created_at: string;
  
  /** 更新时间 (ISO 8601) */
  updated_at: string;
}

/**
 * 洞察卡片列表响应接口
 */
export interface InsightCardListResponse {
  /** 总数 */
  total: number;
  
  /** 洞察卡片列表 */
  items: InsightCard[];
}

