/**
 * TypeScript 类型定义统一导出
 * 
 * 基于 Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-10 Day 1
 * 
 * 使用示例:
 * ```typescript
 * import { User, TaskStatus, AnalyzeRequest } from '@/types';
 * ```
 */

// ============================================================================
// 用户相关类型
// ============================================================================
export {
  SubscriptionTier,
  type User,
  type RegisterRequest,
  type LoginRequest,
  type AuthResponse,
  type UpdateUserRequest,
} from './user.types';

// ============================================================================
// 任务相关类型
// ============================================================================
export {
  TaskStatus,
  type Task,
  type AnalyzeRequest,
  type AnalyzeResponse,
  type TaskProgress,
  type TaskStatusResponse,
} from './task.types';

// ============================================================================
// 分析结果相关类型
// ============================================================================
export {
  Sentiment,
  type ExamplePost,
  type PainPoint,
  type Competitor,
  type Opportunity,
  type Insights,
  type Sources,
  type Analysis,
} from './analysis.types';

// ============================================================================
// 报告相关类型
// ============================================================================
export {
  type ExecutiveSummary,
  type FallbackQuality,
  type ReportMetadata,
  type ReportResponse,
  type ActionItem,
  type EvidenceItem,
} from './report.types';

// ============================================================================
// SSE 相关类型
// ============================================================================
export type {
  SSEEventType,
  SSEConnectionStatus,
  SSEBaseEvent,
  SSEConnectedEvent,
  SSEProgressEvent,
  SSECompletedEvent,
  SSEErrorEvent,
  SSECloseEvent,
  SSEHeartbeatEvent,
  SSEEvent,
  SSEEventHandler,
  SSEClientConfig,
} from './sse.types';

// ============================================================================
// API 通用类型
// ============================================================================
export {
  ErrorSeverity,
  RecoveryStrategy,
  ERROR_CODES,
  type ActionConfidence,
  type RecoveryInfo,
  type RecommendedAction,
  type AlternativeAction,
  type UserActions,
  type ErrorDetail,
  type ErrorResponse,
  type ApiResponse,
  type PaginationParams,
  type PaginationMeta,
  type PaginatedResponse,
  type ErrorCode,
} from './api.types';
