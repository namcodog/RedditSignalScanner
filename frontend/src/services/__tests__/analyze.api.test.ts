import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '@/api/client';
import type { ReportResponse } from '@/types';
import { Sentiment } from '@/types';

vi.mock('@/api/client');

const createMockReport = (taskId: string): ReportResponse => ({
  task_id: taskId,
  status: 'completed',
  generated_at: new Date('2025-01-01T00:00:00Z').toISOString(),
  product_description: 'Mock product description',
  report_html: '<div>report</div>',
  report: {
    executive_summary: {
      total_communities: 5,
      key_insights: 3,
      top_opportunity: 'Simplify onboarding',
    },
    pain_points: [
      {
        description: 'Payment flow is confusing',
        frequency: 12,
        sentiment_score: -0.6,
        severity: 'high',
        example_posts: [
          {
            community: 'r/startups',
            content: 'The payment flow needs too many steps.',
            upvotes: 120,
          },
        ],
        user_examples: ['需要多次点击才能完成支付'],
      },
    ],
    competitors: [
      {
        name: 'CompetitorX',
        mentions: 8,
        sentiment: Sentiment.MIXED,
        strengths: ['Large user base'],
        weaknesses: ['Slow customer support'],
        market_share: 15,
      },
    ],
    opportunities: [
      {
        description: 'Add native integrations',
        relevance_score: 0.85,
        potential_users: 'SaaS founders',
        key_insights: ['Users want automation'],
      },
    ],
    action_items: [
      {
        problem_definition: 'Checkout abandonment is high',
        evidence_chain: [
          {
            title: '用户反馈',
            url: null,
            note: '多位用户提到结账流程冗长',
          },
        ],
        suggested_actions: ['简化结账表单', '引入自动保存进度'],
        confidence: 0.65,
        urgency: 0.7,
        product_fit: 0.6,
        priority: 0.68,
      },
    ],
    entity_summary: {
      brands: [{ name: 'CompetitorX', mentions: 2 }],
      features: [{ name: 'automation', mentions: 3 }],
      pain_points: [{ name: 'confusing', mentions: 1 }],
    },
  },
  metadata: {
    analysis_version: '1.3.0',
    confidence_score: 0.92,
    processing_time_seconds: 14,
    cache_hit_rate: 0.35,
    total_mentions: 240,
  },
  overview: {
    sentiment: {
      positive: 55,
      negative: 30,
      neutral: 15,
    },
    top_communities: [
      {
        name: 'r/startups',
        mentions: 25,
        relevance: 90,
        category: 'startup',
        daily_posts: 180,
      },
    ],
  },
  stats: {
    total_mentions: 240,
    positive_mentions: 60,
    negative_mentions: 90,
    neutral_mentions: 90,
  },
});

describe('analyze.api (P1 改进)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    localStorage.clear();
  });

  it('createAnalyzeTask 应携带超时配置并返回数据', async () => {
    const { createAnalyzeTask } = await import('@/api/analyze.api');

    const payload = { product_description: 'A'.repeat(20) } as any;
    vi.mocked(client.apiClient.post).mockResolvedValue({ data: { task_id: 't1' } } as any);

    const result = await createAnalyzeTask(payload);

    expect(client.apiClient.post).toHaveBeenCalledWith(
      '/analyze',
      payload,
      expect.objectContaining({ timeout: expect.any(Number) })
    );
    expect(result).toEqual({ task_id: 't1' });
  });

  it('createAnalyzeTask 超时应抛出友好错误', async () => {
    const { createAnalyzeTask } = await import('@/api/analyze.api');

    const payload = { product_description: 'B'.repeat(20) } as any;
    const timeoutError: any = new Error('timeout of 20000ms exceeded');
    timeoutError.code = 'ECONNABORTED';

    vi.mocked(client.apiClient.post).mockRejectedValue(timeoutError);

    await expect(createAnalyzeTask(payload)).rejects.toThrow('请求超时，请稍后重试');
  });

  it('getAnalysisReport 应使用缓存（同一 taskId 第二次不再请求）', async () => {
    const { getAnalysisReport } = await import('@/api/analyze.api');

    const report = createMockReport('t2');
    vi.mocked(client.apiClient.get).mockResolvedValue({ data: report } as any);

    const r1 = await getAnalysisReport('t2');
    const r2 = await getAnalysisReport('t2');

    expect(r1).toEqual(report);
    expect(r2).toEqual(report);
    expect(client.apiClient.get).toHaveBeenCalledTimes(1);
  });

  it('getAnalysisReport 命中 localStorage 缓存时不再请求', async () => {
    const now = Date.now();
    const report = createMockReport('cached');
    const storageItem = JSON.stringify({
      data: report,
      expires: now + 60_000,
    });
    localStorage.setItem('report_cache_cached', storageItem);

    const { getAnalysisReport } = await import('@/api/analyze.api');

    const result = await getAnalysisReport('cached');

    expect(client.apiClient.get).not.toHaveBeenCalled();
    expect(result).toEqual(report);
  });

  it('getAnalysisReport 遇到过期缓存时应刷新并写入 localStorage', async () => {
    const expired = JSON.stringify({
      data: createMockReport('expired'),
      expires: Date.now() - 1000,
    });
    localStorage.setItem('report_cache_expired', expired);

    const freshReport = createMockReport('expired');
    vi.mocked(client.apiClient.get).mockResolvedValue({ data: freshReport } as any);

    const { getAnalysisReport } = await import('@/api/analyze.api');
    const result = await getAnalysisReport('expired');

    expect(client.apiClient.get).toHaveBeenCalledTimes(1);
    expect(result).toEqual(freshReport);

    const stored = localStorage.getItem('report_cache_expired');
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.data).toEqual(freshReport);
    expect(parsed.expires).toBeGreaterThan(Date.now());
  });

  it('getAnalysisReport 在请求进行中应复用同一个 Promise', async () => {
    const deferred: { resolve?: (value: any) => void } = {};
    const pendingPromise = new Promise<any>(resolve => {
      deferred.resolve = resolve;
    });

    vi.mocked(client.apiClient.get).mockReturnValue(pendingPromise as any);

    const { getAnalysisReport } = await import('@/api/analyze.api');

    const first = getAnalysisReport('dedupe');
    const second = getAnalysisReport('dedupe');

    expect(first).toBe(second);
    expect(client.apiClient.get).toHaveBeenCalledTimes(1);

    const report = createMockReport('dedupe');
    deferred.resolve!({ data: report });

    await expect(first).resolves.toEqual(report);
  });
});
