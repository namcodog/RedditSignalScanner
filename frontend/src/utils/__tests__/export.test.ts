import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { exportToJSON, exportToCSV, exportToText } from '../export';
import type { ReportResponse } from '@/types';
import { Sentiment } from '@/types';

describe('Export Utils', () => {
  let mockReport: ReportResponse['report'];
  let createElementSpy: any;
  let createObjectURLSpy: any;
  let revokeObjectURLSpy: any;
  let blobConstructorArgs: unknown[][];
  const OriginalBlob = globalThis.Blob;

  beforeEach(() => {
    mockReport = {
      executive_summary: {
        total_communities: 5,
        key_insights: 12,
        top_opportunity: '开发移动端应用',
      },
      pain_points: [
        {
          description: '价格太高',
          frequency: 42,
          sentiment_score: -0.6,
          severity: 'high' as const,
          user_examples: ['太贵了'],
          example_posts: [
            {
              community: 'r/productivity',
              content: '价格太贵了',
              upvotes: 100,
            },
          ],
        },
      ],
      competitors: [
        {
          name: 'Notion',
          mentions: 156,
          sentiment: Sentiment.POSITIVE,
          strengths: ['协作', '模板'],
          weaknesses: ['价格高'],
          market_share: 25,
        },
      ],
      opportunities: [
        {
          description: '开发移动端应用',
          relevance_score: 0.85,
          potential_users: '5000+ 用户',
          key_insights: ['市场需求大'],
        },
      ],
      action_items: [
        {
          problem_definition: '自动化 onboarding 流程',
          evidence_chain: [
            {
              title: '用户抱怨流程复杂',
              url: 'https://reddit.com/r/startups/1',
              note: 'r/startups · 42 赞',
            },
          ],
          suggested_actions: ['进行用户访谈以梳理关键步骤'],
          confidence: 0.8,
          urgency: 0.7,
          product_fit: 0.75,
          priority: 0.42,
        },
      ],
    };

    // Mock DOM APIs
    const mockLink = {
      href: '',
      download: '',
      click: vi.fn(),
    };

    // Mock URL.createObjectURL and revokeObjectURL (not available in Node environment)
    if (!URL.createObjectURL) {
      (URL as any).createObjectURL = vi.fn();
    }
    if (!URL.revokeObjectURL) {
      (URL as any).revokeObjectURL = vi.fn();
    }

    createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
    blobConstructorArgs = [];

    const BlobMock = class extends OriginalBlob {
      constructor(...args: any[]) {
        super(...args);
        blobConstructorArgs.push(args);
      }
    };

    vi.stubGlobal('Blob', BlobMock as unknown as typeof Blob);

    createObjectURLSpy = vi
      .spyOn(URL, 'createObjectURL')
      .mockImplementation((_blob: Blob | MediaSource) => {
        return 'blob:mock-url';
      });
    revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as any);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe('exportToJSON', () => {
    it('应该创建 JSON 文件并触发下载', () => {
      exportToJSON(mockReport, 'task-123');

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(createObjectURLSpy).toHaveBeenCalled();

      const mockLink = createElementSpy.mock.results[0].value;
      expect(mockLink.download).toMatch(/reddit-signal-scanner-task-123-.*\.json/);
      expect(mockLink.click).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalled();
    });

    it('应该包含正确的 JSON 数据', () => {
      exportToJSON(mockReport, 'task-123');

      expect(blobConstructorArgs.length).toBeGreaterThan(0);
      const [parts] = blobConstructorArgs[0] as [unknown[], BlobPropertyBag];
      const jsonContent = String((parts as unknown[])[0]);

      expect(jsonContent).toContain('"total_communities": 5');
      expect(jsonContent).toContain('"top_opportunity": "开发移动端应用"');
    });
  });

  describe('exportToCSV', () => {
    it('应该创建 CSV 文件并触发下载', () => {
      exportToCSV(mockReport, 'task-123');

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(createObjectURLSpy).toHaveBeenCalled();

      const mockLink = createElementSpy.mock.results[0].value;
      expect(mockLink.download).toMatch(/reddit-signal-scanner-task-123-.*\.csv/);
      expect(mockLink.click).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalled();
    });

    it('应该包含 CSV 头部', () => {
      exportToCSV(mockReport, 'task-123');

      expect(blobConstructorArgs.length).toBeGreaterThan(0);
      const [parts] = blobConstructorArgs[0] as [unknown[], BlobPropertyBag];
      const csvContent = String((parts as unknown[])[0]);

      expect(csvContent).toContain('Type,Rank,Text/Name,Score,Details,Keywords/Features');
    });

    it('应该包含痛点数据', () => {
      exportToCSV(mockReport, 'task-123');

      expect(blobConstructorArgs.length).toBeGreaterThan(0);
      const [parts] = blobConstructorArgs[0] as [unknown[], BlobPropertyBag];
      const csvContent = String((parts as unknown[])[0]);

      expect(csvContent).toContain('Pain Point');
      expect(csvContent).toContain('价格太高');
    });
  });

  describe('exportToText', () => {
    it('应该创建文本文件并触发下载', () => {
      exportToText(mockReport, 'task-123');

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(createObjectURLSpy).toHaveBeenCalled();

      const mockLink = createElementSpy.mock.results[0].value;
      expect(mockLink.download).toMatch(/reddit-signal-scanner-task-123-.*\.txt/);
      expect(mockLink.click).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalled();
    });

    it('应该包含报告标题和任务ID', () => {
      exportToText(mockReport, 'task-123');

      expect(blobConstructorArgs.length).toBeGreaterThan(0);
      const [parts] = blobConstructorArgs[0] as [unknown[], BlobPropertyBag];
      const textContent = String((parts as unknown[])[0]);

      expect(textContent).toContain('Reddit Signal Scanner - 分析报告');
      expect(textContent).toContain('任务ID: task-123');
    });

    it('应该包含概览信息', () => {
      exportToText(mockReport, 'task-123');

      expect(blobConstructorArgs.length).toBeGreaterThan(0);
      const [parts] = blobConstructorArgs[0] as [unknown[], BlobPropertyBag];
      const textContent = String((parts as unknown[])[0]);

      expect(textContent).toContain('分析社区数: 5');
      expect(textContent).toContain('关键洞察数: 12');
    });
  });

  describe('错误处理', () => {
    it('exportToJSON 应该在失败时抛出错误', () => {
      createObjectURLSpy.mockImplementation(() => {
        throw new Error('Mock error');
      });

      expect(() => exportToJSON(mockReport, 'task-123')).toThrow('JSON 导出失败');
    });

    it('exportToCSV 应该在失败时抛出错误', () => {
      createObjectURLSpy.mockImplementation(() => {
        throw new Error('Mock error');
      });

      expect(() => exportToCSV(mockReport, 'task-123')).toThrow('CSV 导出失败');
    });

    it('exportToText 应该在失败时抛出错误', () => {
      createObjectURLSpy.mockImplementation(() => {
        throw new Error('Mock error');
      });

      expect(() => exportToText(mockReport, 'task-123')).toThrow('文本导出失败');
    });
  });
});
