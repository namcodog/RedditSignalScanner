/**
 * 任务相关类型定义
 * 
 * 基于 PRD-02 API 设计规范与 Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-11 Day 5
 */

/**
 * 任务状态枚举
 */
export enum TaskStatus {
  /** 待处理 */
  PENDING = 'pending',
  /** 处理中 */
  PROCESSING = 'processing',
  /** 已完成 */
  COMPLETED = 'completed',
  /** 失败 */
  FAILED = 'failed',
}

/**
 * 任务信息接口
 */
export interface Task {
  id: string;
  user_id: string;
  product_description: string;
  status: TaskStatus;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

/**
 * 创建分析任务请求接口
 */
export interface AnalyzeRequest {
  product_description: string;
  /** 可选示例库 ID（用于稳定演示） */
  example_id?: string;
  /** 分析模式：market_insight (市场洞察) 或 operations (运营策略) */
  mode?: 'market_insight' | 'operations';
  /** 审计等级 (调试用) */
  audit_level?: string;
  /** 话题画像 ID (用于锁定赛道) */
  topic_profile_id?: string;
}

/**
 * 创建分析任务响应接口
 */
export interface AnalyzeResponse {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  estimated_completion: string;
  sse_endpoint: string;
}

/**
 * 任务进度信息接口
 */
export interface TaskProgress {
  current_step: string;
  completed_steps: string[];
  total_steps: number;
  percentage: number;
  estimated_remaining?: number;
}

/**
 * 查询任务状态响应接口（与后端 TaskStatusSnapshot 对齐）
 */
export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  progress: number;
  percentage: number;
  message: string;
  current_step: string;
  stage?: string | null;
  blocked_reason?: string | null;
  next_action?: string | null;
  details?: Record<string, unknown> | null;
  error: string | null;
  sse_endpoint: string;
  retry_count: number;
  failure_category: string | null;
  last_retry_at: string | null;
  dead_letter_at: string | null;
  updated_at: string;
}

export interface TaskSourcesResponse {
  task_id: string;
  status: string;
  sources: {
    report_tier: 'A_full' | 'B_trimmed' | 'C_scouting' | 'X_blocked';
    facts_v2_quality?: {
      tier: string;
      flags: string[];
    };
    next_action?: string;
  };
}
