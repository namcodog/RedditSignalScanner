/**
 * ReportPage 单元测试
 * 
 * 基于 Day 7 验收标准
 * 最后更新: 2025-10-13 Day 7
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReportPage from '../ReportPage';
import * as analyzeApi from '@/api/analyze.api';
import type { ReportResponse } from '@/types';
import { Sentiment } from '@/types';

// Mock API
vi.mock('@/api/analyze.api');

// Mock NavigationBreadcrumb
vi.mock('@/components/NavigationBreadcrumb', () => ({
  default: () => <div data-testid="navigation-breadcrumb">Breadcrumb</div>,
}));

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
        example_posts: [],
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

describe('ReportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示加载状态', () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockImplementation(
      () => new Promise(() => {}) // 永不resolve，保持加载状态
    );

    const { container } = render(
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    // 验证骨架屏加载状态（而非文本"加载报告中..."）
    // 骨架屏应该包含动画占位符元素
    const skeletonElements = container.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('应该成功获取并显示报告', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    render(
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '市场洞察报告', level: 2 })).toBeInTheDocument();
    });

    // 验证执行摘要
    expect(screen.getByText('执行摘要')).toBeInTheDocument();
    expect(screen.getByText('分析社区数')).toBeInTheDocument();
    expect(screen.getByText('关键洞察数')).toBeInTheDocument();

    // 验证统计卡片
    expect(screen.getAllByText('用户痛点').length).toBeGreaterThan(0);
    expect(screen.getAllByText('竞品分析').length).toBeGreaterThan(0);
    expect(screen.getAllByText('商业机会').length).toBeGreaterThan(0);

    // 验证行动建议标签与内容
    expect(screen.getAllByText('行动建议').length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole('tab', { name: '行动建议' }));
    await waitFor(() => {
      expect(screen.getByText('自动化 onboarding 流程')).toBeInTheDocument();
    });
  });

  it('应该显示错误状态', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockRejectedValue(
      new Error('Network error')
    );

    render(
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('获取报告失败，请稍后重试')).toBeInTheDocument();
    });

    expect(screen.getByText('返回首页')).toBeInTheDocument();
  });

  it('应该显示元数据信息', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    render(
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('分析元数据')).toBeInTheDocument();
    });

    expect(screen.getByText('1.0')).toBeInTheDocument(); // 版本
    expect(screen.getByText('85%')).toBeInTheDocument(); // 置信度
    expect(screen.getByText('45.6s')).toBeInTheDocument(); // 耗时
    expect(screen.getByText('75%')).toBeInTheDocument(); // 缓存命中率
  });

  it('应该展示痛点、竞品与机会列表', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    render(
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByRole('heading', { name: '市场洞察报告', level: 2 });

    expect(screen.getAllByText('用户痛点').length).toBeGreaterThan(0);
    expect(screen.getByText('缺乏个性化推荐')).toBeInTheDocument();
    expect(screen.getAllByText('竞品分析').length).toBeGreaterThan(0);
    expect(screen.getByText('Product Hunt')).toBeInTheDocument();
    expect(screen.getAllByText('商业机会').length).toBeGreaterThan(0);
    expect(screen.getByText('AI推荐系统')).toBeInTheDocument();
  });

  it('应该显示导出菜单并支持开始新分析', async () => {
    vi.mocked(analyzeApi.getAnalysisReport).mockResolvedValue(mockReport);

    render(
      <MemoryRouter initialEntries={['/report/test-task-id']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '市场洞察报告', level: 2 })).toBeInTheDocument();
    });

    const exportButton = screen.getByRole('button', { name: '导出报告' });
    const startButton = screen.getByRole('button', { name: '开始新分析' });

    expect(exportButton).toBeInTheDocument();
    expect(startButton).toBeInTheDocument();

    await userEvent.click(exportButton);

    expect(screen.getByRole('button', { name: '导出为 JSON' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '导出为 CSV' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '导出为 TXT' })).toBeInTheDocument();
  });
});
