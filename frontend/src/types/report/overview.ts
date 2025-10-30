/**
 * 报告概览（Overview）相关类型
 */

export interface SentimentAnalysis {
  /** 正面情感百分比 */
  positive: number;
  /** 负面情感百分比 */
  negative: number;
  /** 中性情感百分比 */
  neutral: number;
}

export interface TopCommunity {
  /** 社区名称 */
  name: string;
  /** 提及次数 */
  mentions: number;
  /** 相关性百分比 */
  relevance: number;
  /** 社区分类 */
  category?: string | null | undefined;
  /** 每日帖子数 */
  daily_posts?: number | null | undefined;
  /** 平均评论长度 */
  avg_comment_length?: number | null | undefined;
  /** 是否来自缓存 */
  from_cache?: boolean | null | undefined;
  /** 社区成员数 */
  members?: number | null | undefined;
}

export interface Overview {
  /** 市场情感分析 */
  sentiment: SentimentAnalysis;
  /** 热门社区列表（最多5个） */
  top_communities: TopCommunity[];
  /** 总社区数 */
  total_communities?: number | undefined;
  /** Top N 数量 */
  top_n?: number | undefined;
  /** 种子来源 */
  seed_source?: string | null | undefined;
}
