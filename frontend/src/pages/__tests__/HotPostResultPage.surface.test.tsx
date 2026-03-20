import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HotPostResultPage from '../hotpost/HotPostResultPage';
import HotPostSearchPage from '../hotpost/HotPostSearchPage';
import InputPage from '../InputPage';

vi.mock('@/services/hotpost.service', () => ({
  getHotPostResult: vi.fn(),
  generateDeepDiveToken: vi.fn(),
  searchHotPost: vi.fn(),
  subscribeToHotPostStream: vi.fn(() => ({
    disconnect: vi.fn(),
  })),
}));

const mockIsAuthenticated = vi.fn(() => false);

vi.mock('@/api/auth.api', () => ({
  isAuthenticated: () => mockIsAuthenticated(),
}));

vi.mock('@/components/AuthDialog', () => ({
  default: () => null,
}));

vi.mock('@/api/guidance.api', () => ({
  getInputGuidance: vi.fn().mockRejectedValue(new Error('skip guidance')),
}));

import * as hotpostService from '@/services/hotpost.service';

describe('HotPostResultPage Surface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.mockReturnValue(false);
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

  it('应该在快扫加载时展示更像产品的等待态', () => {
    vi.mocked(hotpostService.getHotPostResult).mockImplementation(
      () => new Promise(() => undefined) as any,
    );

    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-1']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('这波热点正在成型')).toBeInTheDocument();
    expect(screen.getByText('系统正在整理摘要、证据和社区。')).toBeInTheDocument();
    expect(screen.getByText('先抓摘要')).toBeInTheDocument();
    expect(screen.getByText('再抓证据')).toBeInTheDocument();
    expect(screen.getByText('最后看社区')).toBeInTheDocument();
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
      expect(screen.getByRole('heading', { name: '这波先决定追不追', level: 2 })).toBeInTheDocument();
    });

    expect(screen.getAllByText('先定追不追').length).toBeGreaterThan(0);
    expect(screen.getByText('现在建议')).toBeInTheDocument();
    expect(screen.getByText('为什么值得继续看')).toBeInTheDocument();
    expect(screen.getByText('用户现在最在意什么')).toBeInTheDocument();
    expect(screen.getAllByText('更安静的夜间清扫').length).toBeGreaterThan(0);
    expect(screen.getByText('下一步动作')).toBeInTheDocument();
    expect(screen.getByText('刚刚扫描')).toBeInTheDocument();
    expect(screen.getByText('值钱就继续深挖。')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '这页先看三件事', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('先看摘要')).toBeInTheDocument();
    expect(screen.getByText('再扫证据')).toBeInTheDocument();
    expect(screen.getByText('最后看社区')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '补充细节（可选）', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '展开补充细节' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '用户现在缺什么', level: 3 })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '关键证据帖', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '这波主要出在哪些社区', level: 3 })).toBeInTheDocument();
    expect(screen.queryByText('⚠️ 预览结果仅供参考，不代表最终市场结论。如需完整决策依据，请生成深度报告。')).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '继续深挖' }).length).toBeGreaterThan(0);
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
      expect(screen.getByRole('heading', { name: '这次快扫还在整理中', level: 3 })).toBeInTheDocument();
    });

    expect(screen.getByText('系统已接到这次搜索，正在重新整理热点信号。先重试一次，不行就换关键词重扫。')).toBeInTheDocument();
    expect(screen.getByText('先重试一次；还不行就换关键词，回搜索页重扫。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新扫描' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '回搜索页重扫' })).toBeInTheDocument();
    expect(screen.queryByText('热点服务暂时不可用')).not.toBeInTheDocument();
  });

  it('应该把重扫 CTA 带回搜索页并恢复原关键词', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-1']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
          <Route path="/hotpost" element={<HotPostSearchPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect((await screen.findAllByRole('button', { name: '回搜索页重扫' })).length).toBeGreaterThan(0);
    screen.getAllByRole('button', { name: '回搜索页重扫' })[0]!.click();

    expect(await screen.findByText('已带回这次搜索方向')).toBeInTheDocument();
    expect(screen.getByText('已带回这次搜索方向。改关键词或补社区后，直接重扫。')).toBeInTheDocument();
    expect((screen.getByRole('textbox', { name: /关键词 \/ 话题/i }) as HTMLInputElement).value).toBe('robot vacuum');
  });

  it('应该把继续深挖 CTA 带回输入页并恢复热点方向', async () => {
    mockIsAuthenticated.mockReturnValue(true);
    vi.mocked(hotpostService.generateDeepDiveToken).mockResolvedValue({
      deepdive_token: 'deep-1',
      expires_in_seconds: 1800,
    });

    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-1']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
          <Route path="/" element={<InputPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect((await screen.findAllByRole('button', { name: '继续深挖' })).length).toBeGreaterThan(0);
    screen.getAllByRole('button', { name: '继续深挖' })[0]!.click();

    expect(await screen.findByText('已带回这次热点方向')).toBeInTheDocument();
    expect(screen.getByText('已带回这次热点方向。补成完整产品描述后，直接继续深挖。')).toBeInTheDocument();
    expect((screen.getByRole('textbox', { name: /产品描述/i }) as HTMLTextAreaElement).value).toBe('robot vacuum');
  });
});
