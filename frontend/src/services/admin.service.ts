/**
 * Admin Dashboard Service
 *
 * 兼容层说明：
 * - admin.api.ts 是前端控制面的唯一 API 真相源
 * - 本文件只保留给旧页面/旧测试的薄兼容壳
 * - 不再自己手搓请求，不再维护第二套接口合同
 */

import * as adminApi from '@/api/admin.api';

export type CommunityData = adminApi.CommunitiesSummaryItem;
export type CommunitySummaryResponse = adminApi.CommunitySummaryResponse;
export type QualityMetrics = adminApi.QualityMetrics;
export type CommunityImportResult = adminApi.CommunityImportResult;
export type CommunityImportHistoryEntry = adminApi.ImportHistoryItem;
export type BetaFeedbackResponse = any;

export const adminService = {
  getCommunities: async (params?: {
    q?: string;
    status?: 'green' | 'yellow' | 'red';
    tag?: string;
    sort?: 'cscore_desc' | 'hit_desc';
    page?: number;
    page_size?: number;
  }): Promise<CommunitySummaryResponse> => {
    return adminApi.getCommunitiesSummary(params);
  },

  getAnalysisTasks: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<{ items: adminApi.TaskLedgerItem[]; total: number }> => {
    return adminApi.getRecentTasks(params ?? {});
  },

  getQualityMetrics: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<QualityMetrics[]> => {
    return adminApi.getQualityMetrics(params);
  },

  getTaskLedger: async (
    taskId: string,
    options?: { includePackage?: boolean },
  ): Promise<adminApi.AdminTaskLedgerResponse> => {
    return adminApi.getTaskLedger(taskId, options?.includePackage);
  },

  getCommunityPool: async (
    params?: Parameters<typeof adminApi.getCommunityPool>[0],
  ): Promise<adminApi.CommunityPoolListResponse> => {
    return adminApi.getCommunityPool(params ?? {});
  },

  getDiscoveredCommunities: async (
    params?: adminApi.DiscoveredCommunitiesParams,
  ): Promise<adminApi.DiscoveredCommunitiesResponse> => {
    return adminApi.getDiscoveredCommunities(params ?? {});
  },

  approveCommunity: async (payload: {
    community_name: string;
    tier?: number;
    categories?: string[];
  }): Promise<adminApi.ApproveCommunityResponse> => {
    return adminApi.approveCommunity({
      name: payload.community_name,
      tier: payload.tier ? `T${payload.tier}` : 'medium',
      categories: payload.categories ? { list: payload.categories } : null,
    });
  },

  rejectCommunity: async (payload: {
    community_name: string;
    reason: string;
  }): Promise<adminApi.RejectCommunityResponse> => {
    return adminApi.rejectCommunity({
      name: payload.community_name,
      admin_notes: payload.reason,
    });
  },

  getDashboardStats: async (): Promise<adminApi.DashboardStats> => {
    return adminApi.getAdminDashboardStats();
  },

  disableCommunity: async (name: string): Promise<{ disabled: string }> => {
    return adminApi.disableCommunity(name);
  },

  getActiveUsers: async (limit?: number): Promise<{ items: adminApi.ActiveUserItem[]; total: number }> => {
    return adminApi.getActiveUsers(limit);
  },

  getTaskQueueStats: async (): Promise<adminApi.TaskQueueStats> => {
    return adminApi.getTaskQueueStats();
  },

  downloadCommunityTemplate: async (): Promise<Blob> => {
    return adminApi.downloadTemplateBlob();
  },

  uploadCommunityImport: async (
    file: File,
    options: { dryRun?: boolean; onProgress?: (percent: number) => void } = {},
  ): Promise<CommunityImportResult> => {
    const importOptions: adminApi.ImportCommunitiesOptions = {};
    if (options.dryRun !== undefined) {
      importOptions.dryRun = options.dryRun;
    }
    if (options.onProgress) {
      importOptions.onUploadProgress = options.onProgress;
    }
    return adminApi.importCommunities(file, importOptions);
  },

  getCommunityImportHistory: async (): Promise<adminApi.ImportHistoryItem[]> => {
    return adminApi.getImportHistory();
  },

  getBetaFeedbackList: async (): Promise<BetaFeedbackResponse> => {
    return adminApi.getBetaFeedbackList();
  },

  getRuntimeDiagnostics: async (): Promise<any> => {
    return adminApi.getRuntimeDiagnostics();
  },

  getTasksDiagnostics: async (): Promise<any> => {
    return adminApi.getTasksDiagnostics();
  },

  batchUpdateCommunityPool: async (
    payload: adminApi.BatchUpdatePayload,
  ): Promise<{ updated_count: number }> => {
    return adminApi.batchUpdateCommunities(payload);
  },

  generateTierSuggestions: async (
    payload: { thresholds?: any; target_communities?: string[] } = {},
  ): Promise<any> => {
    return adminApi.generateTierSuggestions(payload);
  },

  applyTierSuggestions: async (
    payload: { suggestion_ids: number[] },
  ): Promise<{ applied_count: number }> => {
    return adminApi.applyTierSuggestions(payload);
  },

  getTierSuggestions: async (params?: {
    community_name?: string;
    status?: string;
    min_confidence?: number;
    page?: number;
    page_size?: number;
  }): Promise<{ items: adminApi.TierSuggestionItem[]; total: number }> => {
    return adminApi.getTierSuggestions(params ?? {});
  },

  getTierAuditLogs: async (
    communityName: string,
    params?: { page?: number; page_size?: number },
  ): Promise<{ items: adminApi.TierAuditLogItem[]; total: number }> => {
    return adminApi.getCommunityAuditLogs(communityName, params ?? {});
  },

  rollbackTierChange: async (auditLogId: number, reason: string): Promise<any> => {
    return adminApi.rollbackCommunity(auditLogId, reason);
  },

  getCommunityGovernanceSummary: async (): Promise<adminApi.CommunityGovernanceSnapshot> => {
    return adminApi.getCommunityGovernanceSummary();
  },

  getEffectiveCommunities: async (): Promise<{ items: Record<string, any>[]; total: number }> => {
    return adminApi.getEffectiveCommunities();
  },

  cleanupCommunityGovernanceDev: async (
    payload: { dryRun?: boolean } = {},
  ): Promise<Record<string, any>> => {
    return adminApi.cleanupCommunityGovernanceDev({ dry_run: payload.dryRun ?? true });
  },
};
