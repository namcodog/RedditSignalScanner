/**
 * 报告统计（Stats）相关类型
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
