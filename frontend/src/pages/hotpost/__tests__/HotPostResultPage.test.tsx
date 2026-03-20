import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HotPostResultPage from '../HotPostResultPage';

vi.mock('@/services/hotpost.service', () => ({
  getHotPostResult: vi.fn(),
  generateDeepDiveToken: vi.fn(),
  subscribeToHotPostStream: vi.fn(() => ({
    disconnect: vi.fn(),
  })),
}));

vi.mock('@/api/auth.api', () => ({
  isAuthenticated: vi.fn(() => false),
}));

vi.mock('@/components/AuthDialog', () => ({
  default: () => null,
}));

import * as hotpostService from '@/services/hotpost.service';

describe('HotPostResultPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hotpostService.getHotPostResult).mockResolvedValue({
      query_id: 'query-1',
      query: 'robot vacuum',
      mode: 'opportunity',
      search_time: '2026-03-17T10:00:00Z',
      from_cache: false,
      status: 'completed',
      summary: '用户想要更安静、更好打理毛发的扫地机器人。',
      confidence: 'medium',
      evidence_count: 12,
      community_distribution: {
        'r/homeautomation': 7,
        'r/robotvacuums': 5,
      },
      top_posts: [],
      opportunities: [
        {
          need: '更安静的夜间清扫',
          summary: '夜里跑不吵人',
          mentions: 5,
          me_too_count: 3,
          opportunity_signal: 'high',
          current_workarounds: [],
        },
      ],
      communities: ['r/homeautomation', 'r/robotvacuums'],
      next_steps: {
        deepdive_available: true,
        deepdive_token: 'deep-1',
      },
      debug_info: {
        response_source: 'live',
      },
    } as any);
  });

  it('应该在首屏讲清楚 hotpost 是什么、覆盖范围和下一步', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-1']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '这是一份机会快扫', level: 2 })).toBeInTheDocument();
    });

    expect(screen.getByText('这次结果覆盖 2 个社区，抓到 12 条证据。它更适合你先快速判断“有没有料”，不是直接拿来拍最终决策。')).toBeInTheDocument();
    expect(screen.getByText('实时扫描')).toBeInTheDocument();
    expect(screen.getByText('如果这波信号值得追，下一步直接生成深度报告，把快扫变成正式结论。')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '这次还没筛出值得先看的证据帖', level: 3 })).toBeInTheDocument();
    expect(screen.getByText('当前摘要和结论已经有了，但这轮快扫还没留下适合直接翻看的代表性帖子。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成深度报告' })).toBeInTheDocument();
  });

  it('应该在快扫失败时给出统一错误状态和下一步动作', async () => {
    vi.mocked(hotpostService.getHotPostResult).mockRejectedValue(new Error('热点服务暂时不可用'));

    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-1']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '这次快扫还没拿到可用结果', level: 3 })).toBeInTheDocument();
    });

    expect(screen.getByText('热点服务暂时不可用')).toBeInTheDocument();
    expect(screen.getByText('先重试一次；如果还是空，就换个更直白的关键词，或者回到搜索页重新扫。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新扫描' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回搜索' })).toBeInTheDocument();
  });
});
