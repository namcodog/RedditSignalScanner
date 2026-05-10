import { describe, it, expect, beforeEach, vi } from 'vitest';

import { getAnalysisReport } from '@/api/analyze.api';
import {
  collectCanonicalEvidenceLinks,
  validateCanonicalEvidenceLinks,
  validateMarkdownCanonicalAlignment,
} from '@/lib/report-contract';
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
  report_markdown: `# Demo product · 市场洞察报告

## 1. 开篇概览
这条题目前景明确。

## 2. 决策风向标
### 2.1 需求趋势
讨论热度持续稳定。

### 2.2 难题与攻略比
问题略多于答案。

### 2.3 核心社群
r/startups 是核心社群。

### 2.4 落地机会
优先补上离线缓存。

## 3. 概览（市场健康度诊断）
目前仍有切口。

## 4. 核心战场推荐（画像分级）
r/startups 是主战场。

## 5. 用户痛点拆解
用户抱怨响应慢

## 6. 关键决策驱动力
更快得到结果

## 7. 商业机会
引入离线缓存`,
  report_html: '<html></html>',
  canonical_report_json: {
    decision_cards: [
      {
        title: '需求趋势',
        conclusion: '讨论热度持续稳定',
        details: ['高频出现', '已形成稳定需求'],
      },
    ],
    market_health: {
      competition_saturation: {
        level: '中等',
        details: ['已有玩家', '仍有切口'],
        interpretation: '还存在进入空间。',
      },
      ps_ratio: {
        ratio: '1.2:1',
        conclusion: '问题略多于答案',
        interpretation: '用户还在找更好的方案。',
        health_assessment: '机会仍在。',
      },
    },
    battlefields: [
      {
        name: 'r/startups',
        subreddits: ['r/startups'],
        profile: '创业者关心效率和转化。',
        pain_points: ['用户抱怨响应慢'],
        strategy_advice: '优先看增长和留存相关帖子。',
      },
    ],
    pain_points: [
      {
        title: '用户抱怨响应慢',
        user_voices: ['打开以后还要等很久。'],
        data_impression: '反馈集中在加载和等待。',
        interpretation: '慢已经直接影响用户继续使用。',
        evidence_chain: [
          {
            title: '过去一周延迟 > 2s 的反馈',
            url: 'https://www.reddit.com/r/startups/comments/demo',
            note: 'r/startups · 42 upvotes',
          },
        ],
      },
    ],
    drivers: [
      {
        title: '更快得到结果',
        description: '用户愿意为更快响应买单。',
      },
    ],
    opportunities: [
      {
        title: '引入离线缓存',
        target_pain_points: ['用户抱怨响应慢'],
        target_communities: ['r/startups'],
        product_positioning: '先把基础响应速度拉起来。',
        core_selling_points: ['更快打开', '减少等待'],
        evidence_chain: [
          {
            title: '过去一周延迟 > 2s 的反馈',
            url: 'https://www.reddit.com/r/startups/comments/demo',
            note: 'r/startups · 42 upvotes',
          },
        ],
      },
    ],
  },
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
    entity_summary: {
      brands: [{ name: 'CompetitorX', mentions: 3 }],
      features: [{ name: 'cache', mentions: 2 }],
      pain_points: [{ name: 'slow', mentions: 2 }],
    },
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
  sources: {
    communities: ['r/startups'],
    posts_analyzed: 24,
    cache_hit_rate: 0.75,
    analysis_duration_seconds: 18,
    reddit_api_calls: 6,
    data_source: 'real',
    report_tier: 'B_trimmed',
    facts_v2_quality: {
      tier: 'B_trimmed',
      flags: ['pains_low'],
    },
    structured_llm_status: 'skipped',
    structured_llm_reason: 'tier_skipped',
  },
});

describe('Report API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should validate report response shape', async () => {
    (mockedClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: sampleResponse });

    const data = await getAnalysisReport('11111111-1111-1111-1111-111111111111');
    expect(data.report_markdown).toContain('## 7. 商业机会');
    expect(data.canonical_report_json?.decision_cards[0]?.title).toBe('需求趋势');
    expect(data.report.pain_points[0]?.severity).toBe('high');
    expect(data.stats.total_mentions).toBe(150);
    expect(data.sources?.structured_llm_status).toBe('skipped');
    expect(mockedClient.get).toHaveBeenCalled();
  });

  it('should keep markdown/canonical alignment and clickable evidence links', async () => {
    (mockedClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: sampleResponse });

    const data = await getAnalysisReport('11111111-1111-1111-1111-111111111111');
    expect(
      validateMarkdownCanonicalAlignment(data.canonical_report_json, data.report_markdown)
    ).toEqual([]);
    expect(validateCanonicalEvidenceLinks(data.canonical_report_json)).toEqual([]);
    expect(collectCanonicalEvidenceLinks(data.canonical_report_json)).toEqual([
      'https://www.reddit.com/r/startups/comments/demo',
    ]);
  });
});
