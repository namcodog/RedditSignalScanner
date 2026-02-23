/**
 * 报告响应（ReportResponse）类型
 */

import type { Insights } from '../analysis.types';
import type { ExecutiveSummary } from './executive';
import type { ActionItem } from './action-items';
import type { ReportMetadata } from './metadata';
import type { Overview } from './overview';
import type { Stats } from './stats';
import type { EntitySummary } from './entity';

export interface ReportResponse {
  /** 任务 ID (UUID) */
  task_id: string;
  /** 任务状态 */
  status: string;
  /** 报告生成时间 (ISO 8601) */
  generated_at: string;
  /** 产品描述 (允许 null) */
  product_description?: string | null | undefined;
  /** 报告 HTML 快照（用于导出，允许 null） */
  report_html?: string | null | undefined;
  /** 结构化报告（LLM 输出，允许 null） */
  report_structured?: StructuredReport | null | undefined;
  /** 报告内容 */
  report: {
    /** 执行摘要 */
    executive_summary: ExecutiveSummary;
    /** 核心洞察（痛点、竞品、机会） */
    pain_points: Insights['pain_points'];
    competitors: Insights['competitors'];
    opportunities: Insights['opportunities'];
    entity_summary: EntitySummary;
    action_items: ActionItem[];
    purchase_drivers?: { title: string; description: string }[];
    market_health?: {
      competition_saturation?: { level: string; details: string[]; interpretation: string };
      ps_ratio?: { ratio: string; conclusion: string; interpretation: string; health_assessment: string };
    };
  };
  /** 报告元数据 */
  metadata: ReportMetadata;
  /** 概览数据 */
  overview: Overview;
  /** 统计数据 */
  stats: Stats;
}

export interface StructuredReport {
  decision_cards: StructuredDecisionCard[];
  market_health: StructuredMarketHealth;
  battlefields: StructuredBattlefield[];
  pain_points: StructuredPainPoint[];
  drivers: StructuredDriver[];
  opportunities: StructuredOpportunity[];
}

export interface StructuredDecisionCard {
  title: string;
  conclusion: string;
  details: string[];
}

export interface StructuredMarketHealth {
  competition_saturation: {
    level: string;
    details: string[];
    interpretation: string;
  };
  ps_ratio: {
    ratio: string;
    conclusion: string;
    interpretation: string;
    health_assessment: string;
  };
}

export interface StructuredBattlefield {
  name: string;
  subreddits: string[];
  profile: string;
  pain_points?: string[] | undefined;
  strategy_advice: string;
}

export interface StructuredPainPoint {
  title: string;
  user_voices: string[];
  data_impression?: string | undefined;
  interpretation: string;
}

export interface StructuredDriver {
  title: string;
  description: string;
}

export interface StructuredOpportunity {
  title: string;
  target_pain_points: string[];
  target_communities: string[];
  product_positioning: string;
  core_selling_points: string[];
}
