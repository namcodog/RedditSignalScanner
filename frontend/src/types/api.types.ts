/**
 * API 通用类型定义
 * 
 * 基于 Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-10 Day 1
 */

/**
 * 错误严重级别枚举
 */
export enum ErrorSeverity {
  /** 信息 */
  INFO = 'info',
  /** 警告 */
  WARNING = 'warning',
  /** 错误 */
  ERROR = 'error',
  /** 严重错误 */
  CRITICAL = 'critical',
}

/**
 * 恢复策略枚举
 */
export enum RecoveryStrategy {
  /** 降级到缓存 */
  FALLBACK_TO_CACHE = 'fallback_to_cache',
  /** 重试（带退避） */
  RETRY_WITH_BACKOFF = 'retry_with_backoff',
  /** 延迟处理 */
  DELAY_PROCESSING = 'delay_processing',
  /** 部分结果 */
  PARTIAL_RESULTS = 'partial_results',
}

/**
 * 用户操作置信度
 */
export type ActionConfidence = 'high' | 'medium' | 'low';

/**
 * 降级质量信息接口
 */
export interface FallbackQuality {
  /** 缓存覆盖率（0.0 到 1.0） */
  cacheCoverage: number;
  
  /** 数据新鲜度（小时） */
  dataFreshnessHours: number;
  
  /** 估计准确度（0.0 到 1.0） */
  estimatedAccuracy: number;
}

/**
 * 恢复策略信息接口
 */
export interface RecoveryInfo {
  /** 恢复策略 */
  strategy: RecoveryStrategy;
  
  /** 是否自动应用 */
  autoApplied: boolean;
  
  /** 降级质量信息（可选） */
  fallbackQuality?: FallbackQuality;
}

/**
 * 推荐用户操作接口
 */
export interface RecommendedAction {
  /** 操作类型 */
  action: string;
  
  /** 操作标签（用户友好） */
  label: string;
  
  /** 置信度 */
  confidence: ActionConfidence;
}

/**
 * 备选用户操作接口
 */
export interface AlternativeAction {
  /** 操作类型 */
  action: string;
  
  /** 操作标签（用户友好） */
  label: string;
  
  /** 等待时间（秒，可选） */
  waitTime?: number;
}

/**
 * 用户操作建议接口
 */
export interface UserActions {
  /** 推荐操作 */
  recommended: RecommendedAction;
  
  /** 备选操作列表 */
  alternatives: AlternativeAction[];
}

/**
 * 错误详情接口
 */
export interface ErrorDetail {
  /** 错误码 */
  code: string;
  
  /** 用户友好的错误消息 */
  message: string;
  
  /** 错误严重级别 */
  severity: ErrorSeverity;
  
  /** 错误发生时间 (ISO 8601) */
  timestamp: string;
  
  /** 请求追踪 ID */
  requestId: string;
  
  /** 恢复策略信息（可选） */
  recovery?: RecoveryInfo;
  
  /** 用户操作建议（可选） */
  userActions?: UserActions;
}

/**
 * 错误响应接口
 */
export interface ErrorResponse {
  /** 错误详情 */
  error: ErrorDetail;
}

/**
 * API 通用响应接口（泛型）
 */
export interface ApiResponse<T> {
  /** 响应数据 */
  data?: T;
  
  /** 错误信息（如果有） */
  error?: ErrorDetail;
  
  /** 元数据（可选） */
  meta?: {
    /** 请求 ID */
    requestId: string;
    
    /** 响应时间戳 (ISO 8601) */
    timestamp: string;
    
    /** API 版本 */
    version?: string;
  };
}

/**
 * 分页参数接口
 */
export interface PaginationParams {
  /** 页码（从 1 开始） */
  page: number;
  
  /** 每页数量 */
  pageSize: number;
}

/**
 * 分页响应元数据接口
 */
export interface PaginationMeta {
  /** 当前页码 */
  currentPage: number;
  
  /** 每页数量 */
  pageSize: number;
  
  /** 总记录数 */
  totalItems: number;
  
  /** 总页数 */
  totalPages: number;
  
  /** 是否有下一页 */
  hasNext: boolean;
  
  /** 是否有上一页 */
  hasPrevious: boolean;
}

/**
 * 分页响应接口（泛型）
 */
export interface PaginatedResponse<T> {
  /** 数据列表 */
  items: T[];
  
  /** 分页元数据 */
  pagination: PaginationMeta;
}

/**
 * 常见错误码常量
 */
export const ERROR_CODES = {
  /** 产品描述无效 */
  INVALID_DESCRIPTION: 'INVALID_DESCRIPTION',
  /** 任务不存在 */
  TASK_NOT_FOUND: 'TASK_NOT_FOUND',
  /** 报告未生成 */
  REPORT_NOT_READY: 'REPORT_NOT_READY',
  /** Reddit API 限流 */
  REDDIT_API_LIMIT: 'REDDIT_API_LIMIT',
  /** 数据库错误 */
  DATABASE_ERROR: 'DATABASE_ERROR',
  /** 分析超时 */
  ANALYSIS_TIMEOUT: 'ANALYSIS_TIMEOUT',
  /** 请求频率过高 */
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',
  /** SSE 连接失败 */
  SSE_CONNECTION_FAILED: 'SSE_CONNECTION_FAILED',
  /** 未授权 */
  UNAUTHORIZED: 'UNAUTHORIZED',
  /** 禁止访问 */
  FORBIDDEN: 'FORBIDDEN',
  /** 服务器内部错误 */
  INTERNAL_SERVER_ERROR: 'INTERNAL_SERVER_ERROR',
} as const;

/**
 * 错误码类型
 */
export type ErrorCode = typeof ERROR_CODES[keyof typeof ERROR_CODES];

