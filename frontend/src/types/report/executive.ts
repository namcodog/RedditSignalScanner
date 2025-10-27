/**
 * 执行摘要（Executive Summary）相关类型
 * 基于 reports/phase-log/schema-contract.md 契约
 */

export interface ExecutiveSummary {
  /** 分析的社区总数 */
  total_communities: number;
  /** 关键洞察数量 */
  key_insights: number;
  /** 最重要的机会描述 */
  top_opportunity: string;
}
