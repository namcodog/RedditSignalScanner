import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, vi, expect } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import ReportPage from '@/pages/ReportPage';
import { TranslationProvider } from '@/i18n/TranslationProvider';
import * as analyzeApi from '@/api/analyze.api';
import type { ReportResponse } from '@/types';

vi.mock('@/api/analyze.api');
vi.mock('@/components/NavigationBreadcrumb', () => ({
  default: () => <div data-testid="navigation-breadcrumb">Breadcrumb</div>,
}));

// Mock useToast
vi.mock('@/components/ui/toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

const buildReport = (): ReportResponse => ({
  task_id: 'task-123',
  status: 'completed',
  generated_at: '2025-10-25T08:00:00Z',
  product_description: 'Test product',
  report_html: '<html />',
  canonical_report_json: {
    decision_cards: [
      {
        title: '需求趋势',
        conclusion: '讨论热度持续稳定',
        details: ['样本集中在核心社区', '热度持续存在'],
      },
    ],
    market_health: {
      competition_saturation: {
        level: '中等',
        details: ['讨论量稳定', '社区覆盖有限'],
        interpretation: '仍有空间但需差异化。',
      },
      ps_ratio: {
        ratio: '1.2:1',
        conclusion: '问题略多于答案',
        interpretation: '用户仍在找可靠方案。',
        health_assessment: '机会窗口仍在。',
      },
    },
    battlefields: [],
    pain_points: [
      {
        title: '页面加载速度慢',
        user_voices: ['页面打开太久，我经常直接关掉。'],
        data_impression: '抱怨集中在首次打开体验和等待时长。',
        interpretation: '这说明首屏性能已经开始直接影响留存和转化。',
      },
    ],
    drivers: [],
    opportunities: [],
  },
  report_structured: null,
  report: {
    executive_summary: {
      total_communities: 3,
      key_insights: 2,
      top_opportunity: '提升留存率',
    },
    pain_points: [
      {
        text: '页面加载速度慢',
        description: '页面加载速度慢，用户等待超过 5 秒才看到内容。',
        frequency: 18,
        sentiment_score: -0.72,
        severity: 'high',
        example_posts: [],
        user_examples: [],
      },
    ],
    competitors: [],
    opportunities: [],
    action_items: [],
    entity_summary: {
      brands: [],
      features: [],
      pain_points: [],
    },
  },
  metadata: {
    analysis_version: '1.2.0',
    confidence_score: 0.81,
    processing_time_seconds: 21,
    cache_hit_rate: 0.55,
    total_mentions: 320,
  },
  overview: {
    sentiment: {
      positive: 40,
      negative: 35,
      neutral: 25,
    },
    top_communities: [],
  },
  stats: {
    total_mentions: 320,
    positive_mentions: 128,
    negative_mentions: 112,
    neutral_mentions: 80,
  },
  sources: {
    communities: ['r/productivity', 'r/startups'],
    posts_analyzed: 84,
    cache_hit_rate: 0.55,
    analysis_duration_seconds: 21,
    reddit_api_calls: 8,
    data_source: 'real',
    report_tier: 'A_full',
    structured_llm_status: 'completed',
    structured_llm_reason: null,
  },
});

describe('ReportPage 集成流程', () => {
  it('应按当前决策首页 -> 维度选择 -> 详情页流程渲染痛点内容', async () => {
    const report = buildReport();
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(report);
    vi.mocked(analyzeApi.getTaskSources).mockResolvedValue(null as any);

    render(
      <TranslationProvider initialLocale="zh">
        <MemoryRouter initialEntries={['/report/task-123']}>
          <Routes>
            <Route path="/report/:taskId" element={<ReportPage />} />
          </Routes>
        </MemoryRouter>
      </TranslationProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '这次已经值得继续做', level: 2 })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '逐维探索' })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getAllByRole('button', { name: '逐维探索' })[0]!);
    await user.click(screen.getByRole('button', { name: /用户痛点洞察/ }));

    expect(
      screen.getByRole('heading', { name: '用户痛点洞察', level: 2 })
    ).toBeInTheDocument();
    expect(document.body.textContent).toContain('页面加载速度慢');
    expect(document.body.textContent).toContain('这说明首屏性能已经开始直接影响留存和转化');
    expect(screen.getByRole('button', { name: '下一个维度' })).toBeInTheDocument();
  });
});
