import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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

  it('应该按新口径展示模式、信号强度、时间趋势，并在 top_quotes 为空时回退到证据原话', async () => {
    vi.mocked(hotpostService.getHotPostResult).mockResolvedValue({
      query_id: 'query-2',
      query: 'creator marketplace',
      mode: 'trending',
      search_time: '2026-03-17T10:00:00Z',
      from_cache: false,
      status: 'completed',
      summary: '创作者市场这波讨论明显在升温。',
      confidence: 'high',
      evidence_count: 18,
      community_distribution: {
        'r/Entrepreneur': 10,
        'r/sidehustle': 8,
      },
      top_posts: [],
      top_quotes: [],
      topics: [
        {
          rank: 1,
          topic: '创作者撮合平台',
          heat_score: 88,
          time_trend: 'explosive',
          key_takeaway: '品牌和创作者都在找更直接的撮合方式。',
          evidence: [
            {
              title: 'Creators keep asking for direct brand deals',
              score: 56,
              subreddit: 'r/Entrepreneur',
              url: 'https://reddit.com/r/Entrepreneur/1',
              key_quote: 'First buyers keep saying checkout is smoother now.',
            },
          ],
        },
      ],
      communities: ['r/Entrepreneur', 'r/sidehustle'],
      next_steps: {
        deepdive_available: true,
        deepdive_token: 'deep-2',
      },
      debug_info: {
        response_source: 'live',
      },
    } as any);

    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-2']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText('热点追踪').length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText(/✔ 信号可靠/).length).toBeGreaterThan(0);
    expect(screen.getByText('爆发中 NEW')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '代表原话', level: 3 })).toBeInTheDocument();
    expect(screen.getByText(/First buyers keep saying checkout is smoother now\./)).toBeInTheDocument();
  });

  it('应该在用户声音证据模式里先展示真实原话，再展示骂点和帖子', async () => {
    vi.mocked(hotpostService.getHotPostResult).mockResolvedValue({
      query_id: 'query-3',
      query: 'refund flow',
      mode: 'rant',
      search_time: '2026-03-17T10:00:00Z',
      from_cache: false,
      status: 'completed',
      summary: '退款流程的吐槽正在集中。',
      confidence: 'low',
      evidence_count: 6,
      reliability_note: '这轮不是总样本少，更像前排命中还不够准。',
      community_distribution: {
        'r/shopify': 6,
      },
      top_posts: [],
      top_quotes: [
        {
          quote: '退款流程真的太绕了，我每次都要找半天。',
          subreddit: 'r/shopify',
          url: 'https://reddit.com/r/shopify/1',
          created_utc: 1710660000,
        },
      ],
      query_parse: {
        query_kind: 'object',
        subject: 'Shopify',
        focus: '退款流程太绕',
      },
      pain_points: [
        {
          category: '退款流程',
          severity: 'high',
          description: '用户觉得退款环节太绕。',
          sample_quotes: [],
          evidence: [
            {
              title: 'Refund steps are too long',
              score: 24,
              url: 'https://reddit.com/r/shopify/1',
              key_quote: '退款流程真的太绕了，我每次都要找半天。',
            },
          ],
          evidence_posts: [
            {
              rank: 1,
              id: 'post-1',
              title: 'Refund policy made me leave',
              body_preview: 'I was fine until the refund flow buried the actual button.',
              score: 45,
              num_comments: 12,
              subreddit: 'shopify',
              author: 'seller_01',
              reddit_url: 'https://reddit.com/r/shopify/1',
              created_utc: 1710660000,
              signals: ['refund friction'],
              signal_score: 0.92,
              top_comments: [],
            },
          ],
        },
      ],
      competitor_mentions: [
        {
          name: 'Stripe',
          mentions: 4,
          sentiment: 'positive',
          sample_quote: 'Switched to Stripe because refunds there are at least predictable.',
        },
      ],
      migration_intent: {
        considering: '24%',
        total_mentions: 3,
        destinations: [
          {
            name: 'Stripe',
            mentions: 3,
          },
        ],
        key_quote: 'At this point I would rather move the whole checkout to Stripe.',
      },
      communities: ['r/shopify'],
      next_steps: {
        deepdive_available: false,
        deepdive_token: null,
        recommended_actions: ['先把退款入口直接放到订单详情首屏。'],
        suggested_keywords: ['refund button'],
      },
      debug_info: {
        response_source: 'live',
      },
    } as any);

    render(
      <MemoryRouter initialEntries={['/hotpost/result/query-3']}>
        <Routes>
          <Route path="/hotpost/result/:queryId" element={<HotPostResultPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText('用户声音证据').length).toBeGreaterThan(0);
    });

    expect((await screen.findAllByText(/退款流程真的太绕了/)).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: '展开补充细节' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '真实原话', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '用户到底在骂什么', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '代表帖子', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '大家顺手会提到哪些竞品', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '范围说明与下一步', level: 3 })).toBeInTheDocument();
    expect(screen.getByText(/时间：/)).toBeInTheDocument();
    expect(screen.getByText('查看原帖')).toBeInTheDocument();
    expect(screen.getByText('这次系统理解成了什么')).toBeInTheDocument();
    expect(screen.getByText('Refund policy made me leave')).toBeInTheDocument();
    expect(screen.getByText('Stripe')).toBeInTheDocument();
    expect(screen.getByText(/这轮不是总样本少/)).toBeInTheDocument();
    expect(screen.getAllByText(/△ 信号有限/).length).toBeGreaterThan(0);

    const quoteHeading = screen.getByRole('heading', { name: '真实原话', level: 3 });
    const painHeading = screen.getByRole('heading', { name: '用户到底在骂什么', level: 3 });
    const postHeading = screen.getByRole('heading', { name: '代表帖子', level: 3 });
    const compareHeading = screen.getByRole('heading', { name: '大家顺手会提到哪些竞品', level: 3 });
    const rangeHeading = screen.getByRole('heading', { name: '范围说明与下一步', level: 3 });

    expect(quoteHeading.compareDocumentPosition(painHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(painHeading.compareDocumentPosition(postHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(postHeading.compareDocumentPosition(compareHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(compareHeading.compareDocumentPosition(rangeHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('应该在用户声音证据搜索页根据输入先自动识别标签', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost']}>
        <Routes>
          <Route path="/hotpost" element={<HotPostSearchPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByText('用户声音证据'));
    fireEvent.change(screen.getByRole('textbox', { name: /关键词 \/ 话题/i }), {
      target: { value: '为什么 Notion AI 老把我的笔记改写成一堆空话？' },
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue('Notion AI')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('老把我的笔记改写成一堆空话')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '按输入重新识别' })).toBeInTheDocument();
  });
});
