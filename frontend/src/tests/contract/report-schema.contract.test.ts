import { describe, expect, it } from 'vitest';

import { reportResponseSchema } from '@/types';

const buildValidPayload = () => ({
  task_id: '11111111-1111-1111-1111-111111111111',
  status: 'completed',
  generated_at: new Date().toISOString(),
  product_description: 'Market intelligence snapshot',
  report_html: '<html>report</html>',
  report: {
    executive_summary: {
      total_communities: 4,
      key_insights: 3,
      top_opportunity: 'Improve onboarding conversion',
    },
    pain_points: [
      {
        description: 'Users struggle to complete checkout',
        frequency: 12,
        sentiment_score: -0.62,
        severity: 'high',
        example_posts: [
          {
            community: 'r/startups',
            content: 'Checkout flow is too long',
            upvotes: 42,
            url: 'https://reddit.com/r/startups/xyz',
            author: 'founder123',
            permalink: '/r/startups/comments/xyz',
          },
        ],
        user_examples: ['支付页面太复杂', '缺少游客结账'],
      },
    ],
    competitors: [
      {
        name: 'CompetitorX',
        mentions: 18,
        sentiment: 'neutral',
        strengths: ['Strong integrations'],
        weaknesses: ['Slow onboarding'],
        market_share: 24.5,
      },
    ],
    opportunities: [
      {
        description: 'Provide guided onboarding tour',
        relevance_score: 0.82,
        potential_users: 'Product managers',
        key_insights: ['High drop-off in week 1', 'Demand for templates'],
      },
    ],
    action_items: [
      {
        problem_definition: 'Onboarding completion rate below target',
        evidence_chain: [
          {
            title: '用户反馈：引导步骤太多',
            url: 'https://reddit.com/r/startups/xyz',
            note: 'r/startups · 87 upvotes',
          },
        ],
        suggested_actions: ['引入互动式引导', '增加快捷模板'],
        confidence: 0.74,
        urgency: 0.6,
        product_fit: 0.7,
        priority: 0.68,
      },
    ],
  },
  metadata: {
    analysis_version: '2.0.1',
    confidence_score: 0.88,
    processing_time_seconds: 32.5,
    cache_hit_rate: 0.62,
    total_mentions: 640,
    fallback_quality: {
      cache_coverage: 0.82,
      data_freshness_hours: 12,
      estimated_accuracy: 0.78,
    },
  },
  overview: {
    sentiment: {
      positive: 55,
      negative: 25,
      neutral: 20,
    },
    top_communities: [
      {
        name: 'r/startups',
        mentions: 210,
        relevance: 92,
        category: '创业',
        daily_posts: 180,
        avg_comment_length: 48,
        from_cache: false,
        members: 1600000,
      },
    ],
  },
  stats: {
    total_mentions: 640,
    positive_mentions: 280,
    negative_mentions: 210,
    neutral_mentions: 150,
  },
});

describe('reportResponseSchema 契约', () => {
  it('应该接受符合后端契约的有效数据', () => {
    expect(() => reportResponseSchema.parse(buildValidPayload())).not.toThrow();
  });

  it('应该拒绝超出约束的情感百分比', () => {
    const invalid = buildValidPayload();
    invalid.overview.sentiment.positive = 120;

    const result = reportResponseSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });

  it('应该拒绝小数格式的相关性指标', () => {
    const invalid = buildValidPayload();
    if (invalid.overview.top_communities[0]) {
      invalid.overview.top_communities[0].relevance = 0.91 as unknown as number;
    }

    const result = reportResponseSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});
