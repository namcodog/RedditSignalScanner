/**
 * ReportPage 单元测试
 *
 * 覆盖 P3 优化场景：分享功能、可扩展结构、多语言、导出历史、错误信息脱敏
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import * as analyzeApi from '@/api/analyze.api';
import type { ReportResponse } from '@/types';
import { Sentiment } from '@/types';
import { TranslationProvider } from '@/i18n/TranslationProvider';
import ReportPage, { type ReportSectionDefinition } from '../ReportPage';
import { exportToCSV } from '@/utils/export';

// Mock API
vi.mock('@/api/analyze.api');
vi.mock('@/utils/export', () => ({
  exportToJSON: vi.fn(),
  exportToCSV: vi.fn(),
  exportToText: vi.fn(),
}));

// Mock NavigationBreadcrumb，保证页面可渲染
vi.mock('@/components/NavigationBreadcrumb', () => ({
  default: () => <div data-testid="navigation-breadcrumb">Breadcrumb</div>,
}));

const createDeferred = <T,>() => {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

const mockReport: ReportResponse = {
  task_id: 'test-task-id',
  status: 'completed',
  generated_at: '2025-10-13T10:00:00Z',
  report: {
    executive_summary: {
      total_communities: 20,
      key_insights: 15,
      top_opportunity: 'AI驱动的个性化推荐',
    },
    pain_points: [
      {
        description: '缺乏个性化推荐',
        frequency: 342,
        sentiment_score: -0.8,
        severity: 'high' as const,
        user_examples: ['需要更好的推荐'],
        example_posts: [
          {
            community: 'r/startups',
            content: '用户反映推荐列表和兴趣不匹配',
            upvotes: 120,
            url: 'https://reddit.com/r/startups/1',
          },
        ],
      },
    ],
    competitors: [
      {
        name: 'Product Hunt',
        mentions: 1247,
        sentiment: Sentiment.POSITIVE,
        strengths: ['社区活跃'],
        weaknesses: ['商业化不足'],
        market_share: 35,
      },
    ],
    opportunities: [
      {
        description: 'AI推荐系统',
        relevance_score: 0.95,
        potential_users: '中小企业',
        key_insights: ['市场需求大', '技术可行'],
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
        suggested_actions: ['开展用户访谈梳理关键步骤'],
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
    processing_time_seconds: 45.6,
    cache_hit_rate: 0.75,
    total_mentions: 1500,
  },
  overview: {
    sentiment: {
      positive: 58,
      negative: 23,
      neutral: 19,
    },
    top_communities: [
      {
        name: 'r/startups',
        mentions: 500,
        relevance: 89,
        category: '创业',
      },
    ],
  },
  stats: {
    total_mentions: 1500,
    positive_mentions: 870,
    negative_mentions: 345,
    neutral_mentions: 285,
  },
};

const renderReportPage = (
  options?: Partial<{
    locale: 'zh' | 'en';
    sections: ReportSectionDefinition[];
  }>
) => {
  const locale = options?.locale ?? 'zh';
  const sections = options?.sections ?? undefined;

  return render(
    <TranslationProvider initialLocale={locale}>
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage sections={sections} />} />
        </Routes>
      </MemoryRouter>
    </TranslationProvider>
  );
};

describe('ReportPage', () => {
  const originalClipboard = navigator.clipboard;
  const originalShare = (navigator as any).share;

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: originalClipboard,
    });
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: originalShare,
    });
  });

  it('应该显示加载状态', () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockImplementation(
      () => new Promise(() => {})
    );

    const { container } = renderReportPage();

    const skeletonElements = container.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('应该成功获取并显示报告', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '市场洞察报告', level: 2 })).toBeInTheDocument();
    });

    expect(screen.getByText('执行摘要')).toBeInTheDocument();
    expect(screen.getByText('分析社区数')).toBeInTheDocument();
    expect(screen.getByText('关键洞察数')).toBeInTheDocument();

    const user = userEvent.setup();
  await user.click(screen.getByRole('tab', { name: '行动建议' }));
  await waitFor(() => {
    expect(screen.getByText('自动化 onboarding 流程')).toBeInTheDocument();
  });
});

  it('在加载报告时应展示渐进式进度提示', async () => {
    const deferred = createDeferred<ReportResponse>();
    vi.mocked(analyzeApi.getAnalysisReport).mockReturnValue(deferred.promise);

    const { queryByTestId } = renderReportPage();

    act(() => {
      deferred.resolve(mockReport);
    });

    await waitFor(() => {
      const progress = screen.getByTestId('report-loading-progress');
      expect(progress).toHaveAttribute('aria-busy', 'true');
      expect(progress).toHaveTextContent('正在生成视图');
    });

    await waitFor(() => {
      expect(queryByTestId('report-loading-progress')).toBeNull();
    });
  });

  it('导出报告时应显示分阶段的进度条', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);
    vi.mocked(exportToCSV).mockImplementation(async () => {
      await Promise.resolve();
    });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '市场洞察报告', level: 2 })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '导出报告' }));
    await user.click(screen.getByRole('menuitem', { name: '导出为 CSV' }));

    const progress = await screen.findByTestId('report-export-progress');
    expect(progress).toHaveAttribute('role', 'progressbar');

    await waitFor(() => {
      expect(screen.getByTestId('report-export-progress')).toHaveTextContent('导出完成');
    });
  });

  it('当 API 返回详细错误时，应该向用户展示通用提示', async () => {
    const error = new Error('Database connection failed: password=secret');
    Object.assign(error, {
      response: {
        data: {
          detail: 'Detailed internal message',
        },
      },
    });
    vi.mocked(analyzeApi.getAnalysisReport).mockRejectedValue(error);

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText(/获取报告失败，请稍后重试/)).toBeInTheDocument();
    });

    expect(screen.queryByText(/password=secret/)).not.toBeInTheDocument();
  });

  it('应该显示元数据信息', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText('分析元数据')).toBeInTheDocument();
    });

    expect(screen.getByText('1.0')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('45.6s')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('应该展示痛点、竞品与机会列表', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    renderReportPage();

    await screen.findByRole('heading', { name: '市场洞察报告', level: 2 });

    const user = userEvent.setup();

    await user.click(screen.getByRole('tab', { name: '用户痛点' }));
    expect(await screen.findAllByText('缺乏个性化推荐')).not.toHaveLength(0);

    await user.click(screen.getByRole('tab', { name: '竞品分析' }));
    expect(await screen.findAllByText('Product Hunt')).not.toHaveLength(0);

    await user.click(screen.getByRole('tab', { name: '商业机会' }));
    expect(await screen.findAllByText('AI推荐系统')).not.toHaveLength(0);
  });

  it('应该显示导出菜单并记录导出历史', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '市场洞察报告', level: 2 })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '导出报告' }));
    });
    const pdfButton = await screen.findByRole('menuitem', { name: '导出为 PDF' });
    expect(pdfButton).toBeEnabled();
    await act(async () => {
    await user.click(screen.getByRole('menuitem', { name: '导出为 JSON' }));
    });

    expect(screen.getByRole('button', { name: '导出历史' })).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '导出历史' }));
    });

    expect(await screen.findByText(/JSON/)).toBeInTheDocument();
    expect(await screen.findByText(/test-task-id/)).toBeInTheDocument();
  });

  it('在缺少 Web Share API 时会复制链接并提示成功', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: undefined,
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText,
      },
    });

    renderReportPage();

    await screen.findByRole('heading', { name: '市场洞察报告', level: 2 });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '分享' }));
    });
    expect(await screen.findByText('分享链接已复制')).toBeInTheDocument();
  });

  it('允许通过 props 注入新的分区配置', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    const customSections: ReportSectionDefinition[] = [
      {
        id: 'custom',
        label: 'Custom',
        render: () => <div>自定义内容</div>,
      },
    ];

    renderReportPage({ sections: customSections });

    await screen.findByRole('heading', { name: '市场洞察报告', level: 2 });

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: 'Custom' }));
    expect(await screen.findByText('自定义内容')).toBeInTheDocument();
  });

  it('支持英文界面', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    renderReportPage({ locale: 'en' });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Market Insight Report', level: 2 })).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: 'Share' })).toBeInTheDocument();
    const exportButton = screen.getByRole('button', { name: 'Export Report' });
    expect(exportButton).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(exportButton);
    const pdfButton = await screen.findByRole('menuitem', { name: 'Export as PDF' });
    expect(pdfButton).toBeEnabled();
  });
});
