/**
 * admin.service 测试
 *
 * 测试目标: 覆盖率 >90%
 * 测试内容: 所有7个API方法
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminService } from '../admin.service';
import * as client from '@/api/client';

// Mock client
vi.mock('@/api/client');

describe('admin.service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getCommunities', () => {
    it('应该获取社区列表', async () => {
      const mockData = {
        items: [
          {
            community: 'r/test',
            hit_7d: 10,
            last_crawled_at: '2025-10-15',
            dup_ratio: 0.1,
            spam_ratio: 0.05,
            topic_score: 0.8,
            c_score: 0.9,
            status_color: 'green' as const,
            labels: ['tech'],
          },
        ],
        total: 1,
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mockData } });

      const result = await adminService.getCommunities();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/communities/summary', {
        params: undefined,
      });
      expect(result).toEqual(mockData);
    });

    it('应该支持查询参数', async () => {
      const params = {
        status: 'green' as const,
        q: 'test',
        page: 2,
        page_size: 20,
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: { items: [], total: 0 } } });

      await adminService.getCommunities(params);

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/communities/summary', {
        params,
      });
    });
  });

  describe('getAnalysisTasks', () => {
    it('应该获取分析任务列表', async () => {
      const mockResponse = {
        data: {
          items: [
            {
              task_id: 'task-123',
              started_at: '2025-10-15T10:00:00Z',
              duration_seconds: 300,
              communities_count: 10,
              a_score: 0.85,
              must_pass: true,
              satisfaction: true,
            },
          ],
          total: 1,
        },
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await adminService.getAnalysisTasks();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/tasks/recent', {
        params: undefined,
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('应该支持查询参数', async () => {
      const params = {
        limit: 10,
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: { items: [], total: 0 } } });

      await adminService.getAnalysisTasks(params);

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/tasks/recent', {
        params,
      });
    });
  });

  describe('错误处理', () => {
    it('应该正确传递API错误', async () => {
      const error = new Error('API Error');
      vi.mocked(client.apiClient.get).mockRejectedValue(error);

      await expect(adminService.getCommunities()).rejects.toThrow('API Error');
    });

    it('应该正确传递POST错误', async () => {
      const error = new Error('POST Error');
      vi.mocked(client.apiClient.post).mockRejectedValue(error);

      await expect(adminService.approveCommunity({
        community_name: 'r/test',
        tier: 1,
        categories: [],
      })).rejects.toThrow('POST Error');
    });
  });

  describe('P0 新增端点', () => {
    it('getCommunityPool 应该调用正确路径并返回数据', async () => {
      const params = { page: 1, page_size: 10, tier: 1, is_active: true };
      const mock = { items: [], total: 0 };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mock } } as any);
      const result = await adminService.getCommunityPool(params as any);
      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/communities/pool', { params });
      expect(result).toEqual(mock);
    });

    it('getDiscoveredCommunities 应该调用正确路径并返回数据', async () => {
      const params = { page: 1, page_size: 10, min_score: 0.8 };
      const mock = { items: [{ name: 'r/test', score: 0.9 }], total: 1 };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mock } } as any);
      const result = await adminService.getDiscoveredCommunities(params as any);
      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/communities/discovered', { params });
      expect(result).toEqual(mock);
    });

    it('approveCommunity 应该调用正确路径并返回 event_id', async () => {
      const payload = { community_name: 'r/test', tier: 1, categories: ['tech'] };
      vi.mocked(client.apiClient.post).mockResolvedValue({ data: { data: { event_id: 'evt-789' } } } as any);
      const result = await adminService.approveCommunity(payload);
      expect(client.apiClient.post).toHaveBeenCalledWith('/admin/communities/approve', payload);
      expect(result).toEqual({ event_id: 'evt-789' });
    });

    it('rejectCommunity 应该调用正确路径并返回 event_id', async () => {
      const payload = { community_name: 'r/test', reason: 'low_quality' };
      vi.mocked(client.apiClient.post).mockResolvedValue({ data: { data: { event_id: 'evt-999' } } } as any);
      const result = await adminService.rejectCommunity(payload);
      expect(client.apiClient.post).toHaveBeenCalledWith('/admin/communities/reject', payload);
      expect(result).toEqual({ event_id: 'evt-999' });
    });

    it('getDashboardStats 应该调用正确路径并返回统计', async () => {
      const mock = { total_users: 10, total_tasks: 20, total_communities: 30, cache_hit_rate: 0.95 };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mock } } as any);
      const result = await adminService.getDashboardStats();
      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/dashboard/stats');
      expect(result).toEqual(mock);
    });
  });

  describe('社区导入与反馈端点', () => {
    it('downloadCommunityTemplate 应该以 blob 格式下载模板', async () => {
      const blob = new Blob(['test'], { type: 'application/octet-stream' });
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: blob } as any);

      const result = await adminService.downloadCommunityTemplate();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/communities/template', {
        responseType: 'blob',
      });
      expect(result).toBe(blob);
    });

    it('uploadCommunityImport 应该上传文件并返回结果，同时输出进度', async () => {
      const file = new File(['excel'], 'communities.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const mockResponse = {
        status: 'success' as const,
        summary: { total: 1, valid: 1, invalid: 0, duplicates: 0, imported: 1 },
        errors: [],
        communities: [],
      };
      vi.mocked(client.apiClient.post).mockResolvedValue({ data: { data: mockResponse } } as any);
      const progressSpy = vi.fn();

      const result = await adminService.uploadCommunityImport(file, {
        dryRun: true,
        onProgress: progressSpy,
      });

      expect(client.apiClient.post).toHaveBeenCalledWith(
        '/admin/communities/import',
        expect.any(FormData),
        expect.objectContaining({
          params: { dry_run: true },
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: expect.any(Function),
        })
      );
      const callConfig = vi.mocked(client.apiClient.post).mock.calls[0]?.[2];
      if (callConfig && 'onUploadProgress' in callConfig && callConfig.onUploadProgress) {
        callConfig.onUploadProgress({ loaded: 50, total: 100, lengthComputable: true } as any);
      }
      expect(progressSpy).toHaveBeenCalledWith(50);
      expect(result).toEqual(mockResponse);
    });

    it('getCommunityImportHistory 应该返回导入历史数据', async () => {
      const mockHistory = [{ id: 1, filename: 'a.xlsx' }];
      vi.mocked(client.apiClient.get).mockResolvedValue({
        data: { data: { imports: mockHistory } },
      } as any);

      const result = await adminService.getCommunityImportHistory();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/communities/import-history');
      expect(result).toEqual(mockHistory);
    });

    it('getBetaFeedbackList 应该返回用户反馈', async () => {
      const mockFeedback = { items: [{ id: '1', task_id: 't1' }], total: 1 };
      vi.mocked(client.apiClient.get).mockResolvedValue({
        data: { data: mockFeedback },
      } as any);

      const result = await adminService.getBetaFeedbackList();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/beta/feedback');
      expect(result).toEqual(mockFeedback);
    });
  });

  // P1 新增端点
  describe('P1 新增端点', () => {
    it('disableCommunity 应该调用正确路径并返回 disabled', async () => {
      vi.mocked(client.apiClient.delete).mockResolvedValue({ data: { data: { disabled: 'r/test' } } } as any);
      const result = await adminService.disableCommunity('r/test');
      expect(client.apiClient.delete).toHaveBeenCalledWith('/admin/communities/r%2Ftest');
      expect(result).toEqual({ disabled: 'r/test' });
    });

    it('getActiveUsers 应该调用正确路径并返回数据', async () => {
      const mock = { items: [{ user_id: 'u1', email: 'a@b.com', tasks_last_7_days: 3, last_task_at: '2025-10-15T00:00:00Z' }], total: 1 };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mock } } as any);
      const result = await adminService.getActiveUsers(50);
      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/users/active', { params: { limit: 50 } });
      expect(result).toEqual(mock);
    });

    it('getTaskQueueStats 应该调用正确路径并返回原始数据', async () => {
      const mock = { active_workers: 1, active_tasks: 2, reserved_tasks: 3, scheduled_tasks: 4, total_tasks: 9 };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: mock } as any);
      const result = await adminService.getTaskQueueStats();
      expect(client.apiClient.get).toHaveBeenCalledWith('/tasks/stats');
      expect(result).toEqual(mock);
    });
  });

  describe('P2 新增端点', () => {
    it('getRuntimeDiagnostics 应该调用正确路径并返回诊断数据', async () => {
      const mock = {
        timestamp: '2025-10-23T12:00:00Z',
        python: {
          version: '3.11.0',
          executable: '/usr/bin/python3',
          platform: 'Linux',
          architecture: 'x86_64',
        },
        system: {
          cpu_percent: 25.5,
          cpu_count: 8,
          memory_total_mb: 16384,
          memory_available_mb: 8192,
          memory_percent: 50.0,
          disk_usage_percent: 60.0,
        },
        process: {
          pid: 12345,
          memory_rss_mb: 256,
          memory_vms_mb: 512,
          cpu_percent: 5.0,
          num_threads: 10,
          create_time: '2025-10-23T10:00:00Z',
        },
        database: {
          connected: true,
          error: null,
        },
      };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: mock } as any);
      const result = await adminService.getRuntimeDiagnostics();
      expect(client.apiClient.get).toHaveBeenCalledWith('/diag/runtime');
      expect(result).toEqual(mock);
      expect(result.database.connected).toBe(true);
      expect(result.system.cpu_percent).toBeGreaterThan(0);
    });

    it('getTasksDiagnostics 应该调用正确路径并返回配置诊断', async () => {
      const mock = {
        has_reddit_client: true,
        environment: 'development',
      };
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: mock } as any);
      const result = await adminService.getTasksDiagnostics();
      expect(client.apiClient.get).toHaveBeenCalledWith('/tasks/diag');
      expect(result).toEqual(mock);
      expect(result.has_reddit_client).toBe(true);
      expect(result.environment).toBe('development');
    });
  });
});
