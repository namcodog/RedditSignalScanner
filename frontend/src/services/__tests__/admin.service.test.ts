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

  describe('recordCommunityDecision', () => {
    it('应该记录社区决策', async () => {
      const decision = {
        community: 'r/test',
        action: 'approve' as const,
        labels: ['tech'],
        reason: '高质量社区',
      };

      vi.mocked(client.apiClient.post).mockResolvedValue({ data: { data: { event_id: 'evt-123' } } });

      const result = await adminService.recordCommunityDecision(decision);

      expect(client.apiClient.post).toHaveBeenCalledWith('/admin/decisions/community', decision);
      expect(result).toEqual({ event_id: 'evt-123' });
    });
  });

  describe('generatePatch', () => {
    it('应该生成配置补丁', async () => {
      const mockPatch = 'diff --git a/config.yaml b/config.yaml...';

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: mockPatch });

      const result = await adminService.generatePatch();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/config/patch', {
        params: { since: undefined },
        headers: { Accept: 'text/yaml' },
      });
      expect(result).toEqual(mockPatch);
    });

    it('应该支持since参数', async () => {
      const mockPatch = 'diff...';
      const since = '2025-10-01';

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: mockPatch });

      await adminService.generatePatch(since);

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/config/patch', {
        params: { since },
        headers: { Accept: 'text/yaml' },
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

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/analysis/tasks', {
        params: undefined,
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('应该支持查询参数', async () => {
      const params = {
        page: 1,
        page_size: 10,
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: { items: [], total: 0 } } });

      await adminService.getAnalysisTasks(params);

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/analysis/tasks', {
        params,
      });
    });
  });

  describe('recordAnalysisFeedback', () => {
    it('应该记录分析反馈', async () => {
      const feedback = {
        task_id: 'task-123',
        is_satisfied: true,
        reasons: ['quality', 'speed'],
        notes: '分析质量很高',
      };

      vi.mocked(client.apiClient.post).mockResolvedValue({ data: { data: { event_id: 'evt-456' } } });

      const result = await adminService.recordAnalysisFeedback(feedback);

      expect(client.apiClient.post).toHaveBeenCalledWith('/admin/feedback/analysis', feedback);
      expect(result).toEqual({ event_id: 'evt-456' });
    });
  });

  describe('getFeedbackSummary', () => {
    it('应该获取反馈汇总', async () => {
      const mockSummary = {
        analysis_satisfaction_rate: 0.85,
        top_fail_reasons: [
          { reason: 'quality', count: 10 },
          { reason: 'speed', count: 5 },
        ],
        user_like_ratio: 0.9,
        read_complete_rate: 0.75,
        top_flagged_insight_types: [
          { type: 'pain_point', count: 20 },
        ],
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mockSummary } });

      const result = await adminService.getFeedbackSummary();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/feedback/summary', {
        params: { days: 30 },
      });
      expect(result).toEqual(mockSummary);
    });

    it('应该支持自定义天数', async () => {
      const mockSummary = {
        analysis_satisfaction_rate: 0.85,
        top_fail_reasons: [],
        user_like_ratio: 0.9,
        read_complete_rate: 0.75,
        top_flagged_insight_types: [],
      };

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: mockSummary } });

      await adminService.getFeedbackSummary(7);

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/feedback/summary', {
        params: { days: 7 },
      });
    });
  });

  describe('getSystemStatus', () => {
    it('应该获取系统状态', async () => {
      const mockStatus = 'healthy';

      vi.mocked(client.apiClient.get).mockResolvedValue({ data: { data: { status: mockStatus } } });

      const result = await adminService.getSystemStatus();

      expect(client.apiClient.get).toHaveBeenCalledWith('/admin/system/status');
      expect(result).toEqual(mockStatus);
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

      await expect(adminService.recordCommunityDecision({
        community: 'r/test',
        action: 'approve',
        labels: [],
        reason: 'test',
      })).rejects.toThrow('POST Error');
    });
  });
});

