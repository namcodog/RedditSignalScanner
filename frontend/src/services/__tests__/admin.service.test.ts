import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminService } from '../admin.service';
import * as adminApi from '@/api/admin.api';

vi.mock('@/api/admin.api', () => ({
  getCommunitiesSummary: vi.fn(),
  getRecentTasks: vi.fn(),
  getQualityMetrics: vi.fn(),
  getTaskLedger: vi.fn(),
  getCommunityPool: vi.fn(),
  getDiscoveredCommunities: vi.fn(),
  approveCommunity: vi.fn(),
  rejectCommunity: vi.fn(),
  getAdminDashboardStats: vi.fn(),
  disableCommunity: vi.fn(),
  getActiveUsers: vi.fn(),
  getTaskQueueStats: vi.fn(),
  downloadTemplateBlob: vi.fn(),
  importCommunities: vi.fn(),
  getImportHistory: vi.fn(),
  getBetaFeedbackList: vi.fn(),
  getRuntimeDiagnostics: vi.fn(),
  getTasksDiagnostics: vi.fn(),
  batchUpdateCommunities: vi.fn(),
  generateTierSuggestions: vi.fn(),
  applyTierSuggestions: vi.fn(),
  getTierSuggestions: vi.fn(),
  getCommunityAuditLogs: vi.fn(),
  rollbackCommunity: vi.fn(),
  getCommunityGovernanceSummary: vi.fn(),
  getEffectiveCommunities: vi.fn(),
  cleanupCommunityGovernanceDev: vi.fn(),
}));

describe('admin.service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getCommunities 应该委托给 admin.api 的社区汇总接口', async () => {
    const mock = { items: [{ community: 'r/test' }], total: 1 } as any;
    vi.mocked(adminApi.getCommunitiesSummary).mockResolvedValue(mock);

    const result = await adminService.getCommunities({ q: 'test', page: 2 });

    expect(adminApi.getCommunitiesSummary).toHaveBeenCalledWith({ q: 'test', page: 2 });
    expect(result).toEqual(mock);
  });

  it('getAnalysisTasks 应该委托给 admin.api 的 recent tasks 接口', async () => {
    const mock = { items: [], total: 0 };
    vi.mocked(adminApi.getRecentTasks).mockResolvedValue(mock);

    const result = await adminService.getAnalysisTasks({ limit: 10 });

    expect(adminApi.getRecentTasks).toHaveBeenCalledWith({ limit: 10 });
    expect(result).toEqual(mock);
  });

  it('approveCommunity 应该做旧参数到新接口的兼容转换', async () => {
    const mock = { approved: 'r/test', pool_is_active: true };
    vi.mocked(adminApi.approveCommunity).mockResolvedValue(mock);

    const result = await adminService.approveCommunity({
      community_name: 'r/test',
      tier: 1,
      categories: ['tech'],
    });

    expect(adminApi.approveCommunity).toHaveBeenCalledWith({
      name: 'r/test',
      tier: 'T1',
      categories: { list: ['tech'] },
    });
    expect(result).toEqual(mock);
  });

  it('rejectCommunity 应该做旧参数到新接口的兼容转换', async () => {
    const mock = { rejected: 'r/test' };
    vi.mocked(adminApi.rejectCommunity).mockResolvedValue(mock);

    const result = await adminService.rejectCommunity({
      community_name: 'r/test',
      reason: 'low_quality',
    });

    expect(adminApi.rejectCommunity).toHaveBeenCalledWith({
      name: 'r/test',
      admin_notes: 'low_quality',
    });
    expect(result).toEqual(mock);
  });

  it('uploadCommunityImport 应该把 dryRun 和 onProgress 传给 admin.api', async () => {
    const file = new File(['excel'], 'communities.xlsx');
    const progressSpy = vi.fn();
    const mock = { status: 'ok', summary: { total: 1, valid: 1, invalid: 0, duplicates: 0, imported: 1 } } as any;
    vi.mocked(adminApi.importCommunities).mockResolvedValue(mock);

    const result = await adminService.uploadCommunityImport(file, {
      dryRun: true,
      onProgress: progressSpy,
    });

    expect(adminApi.importCommunities).toHaveBeenCalledWith(file, {
      dryRun: true,
      onUploadProgress: progressSpy,
    });
    expect(result).toEqual(mock);
  });

  it('downloadCommunityTemplate 应该委托给 blob 下载接口', async () => {
    const blob = new Blob(['test']);
    vi.mocked(adminApi.downloadTemplateBlob).mockResolvedValue(blob);

    const result = await adminService.downloadCommunityTemplate();

    expect(adminApi.downloadTemplateBlob).toHaveBeenCalled();
    expect(result).toBe(blob);
  });

  it('治理快照相关方法应该统一委托给 admin.api', async () => {
    vi.mocked(adminApi.getCommunityGovernanceSummary).mockResolvedValue({ summary: {} } as any);
    vi.mocked(adminApi.getEffectiveCommunities).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(adminApi.cleanupCommunityGovernanceDev).mockResolvedValue({ dry_run: true } as any);

    await adminService.getCommunityGovernanceSummary();
    await adminService.getEffectiveCommunities();
    await adminService.cleanupCommunityGovernanceDev({ dryRun: false });

    expect(adminApi.getCommunityGovernanceSummary).toHaveBeenCalled();
    expect(adminApi.getEffectiveCommunities).toHaveBeenCalled();
    expect(adminApi.cleanupCommunityGovernanceDev).toHaveBeenCalledWith({ dry_run: false });
  });

  it('诊断类接口应该统一委托给 admin.api', async () => {
    vi.mocked(adminApi.getRuntimeDiagnostics).mockResolvedValue({ ok: true });
    vi.mocked(adminApi.getTasksDiagnostics).mockResolvedValue({ ok: true });

    expect(await adminService.getRuntimeDiagnostics()).toEqual({ ok: true });
    expect(await adminService.getTasksDiagnostics()).toEqual({ ok: true });
    expect(adminApi.getRuntimeDiagnostics).toHaveBeenCalled();
    expect(adminApi.getTasksDiagnostics).toHaveBeenCalled();
  });
});
