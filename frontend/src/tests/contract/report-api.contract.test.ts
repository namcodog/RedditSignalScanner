import { describe, it, expect, beforeEach, vi } from 'vitest';

import { getAnalysisReport } from '@/api/analyze.api';
import { reportResponseSchema } from '@/types';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';

const mockedClient = vi.mocked(apiClient);

const sampleResponse = reportResponseSchema.parse({
  task_id: '11111111-1111-1111-1111-111111111111',
  status: 'completed',
  generated_at: new Date().toISOString(),
  product_description: 'Demo product',
  report_html: '<html></html>',
  report: {
    executive_summary: {
      total_communities: 2,
      key_insights: 3,
      top_opportunity: '优化转化漏斗',
    },
    pain_points: [
      {
        description: '用户抱怨响应慢',
        frequency: 5,
        sentiment_score: -0.7,
        severity: 'high',
        example_posts: [],
        user_examples: ['加载太慢了'],
      },
    ],
    competitors: [
      {
        name: 'CompetitorX',
        mentions: 12,
        sentiment: 'positive',
        strengths: ['UI 简洁'],
        weaknesses: ['定价昂贵'],
        market_share: 35,
      },
    ],
    opportunities: [
      {
        description: '引入离线缓存',
        relevance_score: 0.85,
        potential_users: '个人用户',
        key_insights: ['高频反馈', '技术可行'],
      },
    ],
    action_items: [
      {
        problem_definition: '服务器响应延迟过高',
        evidence_chain: [
          {
            title: '过去一周延迟 > 2s 的反馈',
            url: null,
            note: 'r/startups · 42 upvotes',
          },
        ],
        suggested_actions: ['新增性能监控', '优化缓存策略'],
        confidence: 0.8,
        urgency: 0.7,
        product_fit: 0.75,
        priority: 0.42,
      },
    ],
  },
  metadata: {
    analysis_version: '1.0',
    confidence_score: 0.85,
    processing_time_seconds: 45,
    cache_hit_rate: 0.75,
    total_mentions: 150,
  },
  overview: {
    sentiment: {
      positive: 60,
      negative: 20,
      neutral: 20,
    },
    top_communities: [
      {
        name: 'r/startups',
        mentions: 50,
        relevance: 90,
        category: '创业',
        daily_posts: 120,
        avg_comment_length: 32,
        from_cache: false,
        members: 1200000,
      },
    ],
  },
  stats: {
    total_mentions: 150,
    positive_mentions: 90,
    negative_mentions: 30,
    neutral_mentions: 30,
  },
});

describe('Report API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should validate report response shape', async () => {
    (mockedClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: sampleResponse });

    const data = await getAnalysisReport('11111111-1111-1111-1111-111111111111');
    expect(data.report.pain_points[0]?.severity).toBe('high');
    expect(data.stats.total_mentions).toBe(150);
    expect(mockedClient.get).toHaveBeenCalled();
  });
});
