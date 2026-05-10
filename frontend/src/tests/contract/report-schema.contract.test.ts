import { describe, expect, it } from 'vitest';

import {
  collectCanonicalEvidenceLinks,
  validateCanonicalEvidenceLinks,
  validateMarkdownCanonicalAlignment,
} from '@/lib/report-contract';
import { reportResponseSchema } from '@/types';

const buildValidPayload = () => ({
  task_id: '11111111-1111-1111-1111-111111111111',
  status: 'completed',
  generated_at: new Date().toISOString(),
  product_description: 'Market intelligence snapshot',
  report_markdown: `# Full A report

## 1. 开篇概览
这是一条值得继续看的市场切片。

## 2. 决策风向标
### 2.1 需求趋势
需求趋势显示讨论持续存在。

### 2.2 难题与攻略比
难题与攻略比说明问题还多于答案。

### 2.3 核心社群
核心社群集中在 r/startups。

### 2.4 落地机会
落地机会先从引导体验切入。

## 3. 概览（市场健康度诊断）
市场健康度显示仍有差异化空间。

## 4. 核心战场推荐（画像分级）
r/startups 是当前最值得长期蹲守的战场。

## 5. 用户痛点拆解
支付页面太复杂

## 6. 关键决策驱动力
更快完成上手

## 7. 商业机会
引导式新手上手包`,
  report_html: '<html>report</html>',
  canonical_report_json: {
    decision_cards: [
      {
        title: '需求趋势',
        conclusion: '需求稳定存在',
        details: ['跨社区复现', '持续有新帖出现'],
      },
    ],
    market_health: {
      competition_saturation: {
        level: '中等',
        details: ['已有玩家', '仍有空间'],
        interpretation: '适合找差异化切口。',
      },
      ps_ratio: {
        ratio: '1.3:1',
        conclusion: '问题仍略多于答案',
        interpretation: '说明用户还没被完全满足。',
        health_assessment: '可以继续深挖。',
      },
    },
    battlefields: [
      {
        name: 'r/startups',
        subreddits: ['r/startups'],
        profile: '创业团队在这里集中讨论增长和效率。',
        pain_points: ['支付页面太复杂'],
        strategy_advice: '优先看 onboarding 与转化相关讨论。',
      },
    ],
    pain_points: [
      {
        title: '支付页面太复杂',
        user_voices: ['我每次都在最后一步流失'],
        data_impression: '抱怨集中在结账步骤过长。',
        interpretation: '复杂流程已经直接影响成交。',
        evidence_chain: [
          {
            title: '用户反馈：引导步骤太多',
            url: 'https://www.reddit.com/r/startups/comments/xyz',
            note: 'r/startups · 87 upvotes',
          },
        ],
      },
    ],
    drivers: [
      {
        title: '更快完成上手',
        description: '用户愿意为更少试错和更短上手时间买单。',
      },
    ],
    opportunities: [
      {
        title: '引导式新手上手包',
        target_pain_points: ['支付页面太复杂'],
        target_communities: ['r/startups'],
        product_positioning: '把首次转化路径压到最短。',
        core_selling_points: ['减少流失', '降低学习成本'],
        evidence_chain: [
          {
            title: '用户反馈：引导步骤太多',
            url: 'https://www.reddit.com/r/startups/comments/xyz',
            note: 'r/startups · 87 upvotes',
          },
        ],
      },
    ],
  },
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
    entity_summary: {
      brands: [
        { name: 'CompetitorX', mentions: 3 },
        { name: 'CompetitorY', mentions: 2 },
      ],
      features: [{ name: 'automation', mentions: 4 }],
      pain_points: [{ name: 'confusing', mentions: 2 }],
    },
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
  sources: {
    communities: ['r/startups', 'r/entrepreneur'],
    posts_analyzed: 128,
    cache_hit_rate: 0.62,
    analysis_duration_seconds: 33,
    reddit_api_calls: 12,
    product_description: 'Market intelligence snapshot',
    communities_detail: [
      {
        name: 'r/startups',
        categories: ['Ecommerce_Business'],
        mentions: 42,
        daily_posts: 180,
        avg_comment_length: 48,
        cache_hit_rate: 0.5,
        from_cache: false,
      },
    ],
    data_source: 'real',
    report_tier: 'A_full',
    structured_llm_status: 'completed',
    structured_llm_reason: null,
    llm_used: true,
    llm_model: 'gpt-5.3-low',
    llm_rounds: 1,
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

  it('应该接受后端新增的 sources 契约字段', () => {
    const parsed = reportResponseSchema.parse(buildValidPayload());
    expect(parsed.report_markdown).toContain('## 1. 开篇概览');
    expect(parsed.sources?.report_tier).toBe('A_full');
    expect(parsed.canonical_report_json?.decision_cards[0]?.conclusion).toBe('需求稳定存在');
    expect(parsed.sources?.communities_detail?.[0]?.name).toBe('r/startups');
  });

  it('应该保证 markdown 与 canonical_report_json 的 1-7 结构对齐', () => {
    const parsed = reportResponseSchema.parse(buildValidPayload());
    const issues = validateMarkdownCanonicalAlignment(
      parsed.canonical_report_json,
      parsed.report_markdown
    );
    expect(issues).toEqual([]);
  });

  it('应该保证 canonical 证据链都能转成可点击 Reddit 链接', () => {
    const parsed = reportResponseSchema.parse(buildValidPayload());
    expect(validateCanonicalEvidenceLinks(parsed.canonical_report_json)).toEqual([]);
    expect(collectCanonicalEvidenceLinks(parsed.canonical_report_json)).toEqual([
      'https://www.reddit.com/r/startups/comments/xyz',
    ]);
  });

  it('应该拒绝 markdown 缺段或 evidence 不可点击的合同漂移', () => {
    const invalid = buildValidPayload();
    invalid.report_markdown = '# Broken\n\n## 1. 开篇概览\n只有第一段';
    invalid.canonical_report_json.pain_points[0]!.evidence_chain![0]!.url = 'https://example.com/not-reddit';

    const parsed = reportResponseSchema.parse(invalid);
    expect(
      validateMarkdownCanonicalAlignment(
        parsed.canonical_report_json,
        parsed.report_markdown
      ).length
    ).toBeGreaterThan(0);
    expect(validateCanonicalEvidenceLinks(parsed.canonical_report_json)).toContain(
      'pain evidence is not clickable: 支付页面太复杂'
    );
  });
});
