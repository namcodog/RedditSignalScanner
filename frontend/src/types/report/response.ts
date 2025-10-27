/**
 * 报告响应（ReportResponse）类型
 */

import type { Insights } from '../analysis.types';
import type { ExecutiveSummary } from './executive';
import type { ActionItem } from './action-items';
import type { ReportMetadata } from './metadata';
import type { Overview } from './overview';
import type { Stats } from './stats';

export interface ReportResponse {
  /** 任务 ID (UUID) */
  task_id: string;
  /** 任务状态 */
  status: string;
  /** 报告生成时间 (ISO 8601) */
  generated_at: string;
  /** 产品描述 */
  product_description?: string | undefined;
  /** 报告 HTML 快照（用于导出） */
  report_html?: string | undefined;
  /** 报告内容 */
  report: {
    /** 执行摘要 */
    executive_summary: ExecutiveSummary;
    /** 核心洞察（痛点、竞品、机会） */
    pain_points: Insights['pain_points'];
    competitors: Insights['competitors'];
    opportunities: Insights['opportunities'];
    action_items: ActionItem[];
  };
  /** 报告元数据 */
  metadata: ReportMetadata;
  /** 概览数据 */
  overview: Overview;
  /** 统计数据 */
  stats: Stats;
}
