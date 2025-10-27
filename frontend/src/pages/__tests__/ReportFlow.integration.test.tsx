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

const buildReport = (): ReportResponse => ({
  task_id: 'task-123',
  status: 'completed',
  generated_at: '2025-10-25T08:00:00Z',
  product_description: 'Test product',
  report_html: '<html />',
  report: {
    executive_summary: {
      total_communities: 3,
      key_insights: 2,
      top_opportunity: '提升留存率',
    },
    pain_points: [
      {
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
});

describe('ReportPage 集成流程', () => {
  it('应渲染归一化后的痛点并复用共享空状态', async () => {
    const report = buildReport();
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(report);

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
      expect(screen.getByRole('heading', { name: '市场洞察报告', level: 2 })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: '用户痛点' }));

    expect(
      screen.getByRole('heading', { name: /页面加载速度慢/ })
    ).toBeInTheDocument();
    // 正常化后应该提取描述作为用户示例
    expect(screen.getByText(/用户示例/)).toBeInTheDocument();

    // 行动建议为空时使用共享空状态组件
    await user.click(screen.getByRole('tab', { name: '行动建议' }));
    await waitFor(() => {
      expect(document.body.textContent).toContain('暂无行动建议');
    });
  });
});
