/**
 * Admin 控制面前端 API 真相源（薄 barrel）
 *
 * 第二轮结构性收口：
 * - 各域 API 已拆到 ./admin/*.api.ts
 * - 本文件只保留显式 re-export，继续作为页面和兼容层的统一入口
 * - 不再承载具体请求实现，避免重新长成 God file
 */

export {
  type DashboardStats,
  getAdminDashboardStats,
} from './admin/dashboard.api';

export {
  type CommunitiesSummaryItem,
  type CommunitySummaryResponse,
  getCommunitiesSummary,
  type EvidencePost,
  type DiscoveredCommunityItem,
  type DiscoveredCommunitiesResponse,
  type DiscoveredCommunitiesParams,
  getDiscoveredCommunities,
  type ApproveCommunityRequest,
  type ApproveCommunityResponse,
  approveCommunity,
  type RejectCommunityRequest,
  type RejectCommunityResponse,
  rejectCommunity,
  type CommunityPoolItem,
  type CommunityPoolListResponse,
  getCommunityPool,
  type BatchUpdatePayload,
  batchUpdateCommunities,
  disableCommunity,
  type TierSuggestionItem,
  getTierSuggestions,
  generateTierSuggestions,
  applyTierSuggestions,
  type TierAuditLogItem,
  getCommunityAuditLogs,
  rollbackCommunity,
} from './admin/communities.api';

export {
  downloadTemplateBlob,
  downloadTemplate,
  type CommunityImportSummary,
  type CommunityImportResult,
  type ImportCommunitiesOptions,
  importCommunities,
  type ImportHistoryItem,
  getImportHistory,
} from './admin/imports.api';

export {
  type CommunityGovernanceSnapshot,
  getCommunityGovernanceSummary,
  getEffectiveCommunities,
  cleanupCommunityGovernanceDev,
} from './admin/governance.api';

export {
  type ActiveUserItem,
  getActiveUsers,
  type TaskQueueStats,
  getTaskQueueStats,
  type QualityMetrics,
  getQualityMetrics,
  getBetaFeedbackList,
  getRuntimeDiagnostics,
  getTasksDiagnostics,
  type TaskLedgerItem,
  getRecentTasks,
  type AdminTaskLedgerResponse,
  getTaskLedger,
} from './admin/tasks.api';
