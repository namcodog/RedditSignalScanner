/**
 * 行动项（Action Items）相关类型
 */

export interface EvidenceItem {
  /** 证据标题或摘要 */
  title: string;
  /** 证据链接（可能为空） */
  url?: string | null;
  /** 补充说明 */
  note: string;
}

export interface ActionItem {
  problem_definition: string;
  evidence_chain: EvidenceItem[];
  suggested_actions: string[];
  confidence: number;
  urgency: number;
  product_fit: number;
  priority: number;
}
