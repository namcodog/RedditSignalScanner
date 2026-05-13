import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReportPage from '../ReportPage';
import InputPage from '../InputPage';
import * as analyzeApiModule from '@/api/analyze.api';

vi.mock('@/api/guidance.api', () => ({
  getInputGuidance: vi.fn().mockRejectedValue(new Error('skip guidance')),
}));

// Mock API
vi.mock('@/api/analyze.api', () => ({
  getAnalysisReport: vi.fn(),
  getTaskSources: vi.fn(),
  createAnalyzeTask: vi.fn(),
}));

describe('ReportPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该在报告加载时展示更像产品的整理态', () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockImplementation(
      () => new Promise(() => undefined) as any
    );
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('正在整理这次判断')).toBeInTheDocument();
    expect(
      screen.getByText(
        '先帮你把市场温度、用户抱怨和可追机会捞出来，马上就能进正式判断。'
      )
    ).toBeInTheDocument();
    expect(screen.getByText('市场温度')).toBeInTheDocument();
    expect(screen.getByText('用户抱怨')).toBeInTheDocument();
    expect(screen.getByText('可追机会')).toBeInTheDocument();
  });

  it('renders report page', async () => {
    // Basic test just to ensure component mounts
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: '123',
      status: 'completed',
      generated_at: '2023-01-01',
      report_markdown:
        '# 跨境电商卖家多平台回款管理工具 · 市场洞察报告\n\n## 1. 开篇概览\n这是一份完整正文。\n\n## 2. 决策风向标\n**需求趋势**\n讨论热度持续稳定。\n\n## 3. 概览（市场健康度诊断）\n可继续推进。',
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
        pain_points: [],
        drivers: [],
        opportunities: [
          {
            title: '多平台回款聚合器',
            target_communities: ['r/tiktokshop'],
            target_pain_points: ['结算周期长卡资金'],
            product_positioning:
              '一键抓 Amazon/Etsy/Shopify/TikTok 回款，费率透明不漏扣',
            core_selling_points: [],
          },
        ],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.9,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 100,
      },
      overview: {
        sentiment: { positive: 10, negative: 10, neutral: 80 },
        top_communities: [],
        total_communities: 0,
      },
      stats: {
        total_mentions: 0,
        positive_mentions: 0,
        negative_mentions: 0,
        neutral_mentions: 0,
      },
      sources: {
        communities: ['r/startups'],
        posts_analyzed: 16,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'A_full',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 0,
          key_insights: 0,
          top_opportunity: 'test',
        },
        pain_points: [],
        competitors: [],
        opportunities: [
          {
            title: 'need to connect my',
            description: 'need to connect my Shopify store to my TikTok page',
            relevance_score: 0.82,
            potential_users: '多平台经营的跨境卖家',
            key_insights: ['回款口径分散', '手续费不透明', '手工对账耗时'],
          },
        ],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      report_structured: null,
    });
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('讨论热度持续稳定')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '这次已经值得继续做', level: 2 })
    ).toBeInTheDocument();
    expect(screen.getByText('可直接看结论')).toBeInTheDocument();
    expect(screen.getByText('先拍第一板')).toBeInTheDocument();
    expect(screen.getByText('现在建议')).toBeInTheDocument();
    expect(screen.getByText('可以拍第一板')).toBeInTheDocument();
    expect(screen.getByText('拍板依据')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '支持拍板的 3 条证据', level: 2 })
    ).toBeInTheDocument();
    expect(
      screen.getByText('先把最能支撑拍板的三条信号看完。')
    ).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '逐维探索' })).toHaveLength(1);
    expect(screen.getAllByRole('button', { name: '看完整报告' })).toHaveLength(
      1
    );
    expect(
      screen.getByRole('heading', { name: '如果还想继续，再往下看', level: 2 })
    ).toBeInTheDocument();
    expect(screen.getByText('先挑最影响拍板的一块看。')).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: '市场洞察报告已生成', level: 1 })
    ).not.toBeInTheDocument();

    screen.getByRole('button', { name: '看完整报告' }).click();

    await waitFor(() => {
      expect(
        screen.getByText('和卡片同一颗粒度的完整正文')
      ).toBeInTheDocument();
    });
    expect(screen.getByText('1. 开篇概览')).toBeInTheDocument();
    expect(screen.queryByText('## 1. 开篇概览')).not.toBeInTheDocument();
  });

  it('应该把相对 permalink 规范成可直达 Reddit 的证据链接', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: '123',
      status: 'completed',
      generated_at: '2023-01-01',
      report_markdown:
        '# 报告\n\n## 1. 开篇概览\n概览。\n\n## 2. 决策风向标\n**需求趋势**\n继续看。\n\n## 3. 概览（市场健康度诊断）\n可继续推进。',
      canonical_report_json: {
        decision_cards: [
          {
            title: '需求趋势',
            conclusion: '继续看',
            details: ['样本够用', '方向明确'],
          },
        ],
        market_health: {
          competition_saturation: {
            level: '中等',
            details: ['讨论稳定', '需求明确'],
            interpretation: '还有切口。',
          },
          ps_ratio: {
            ratio: '0.6',
            conclusion: '痛点多于解法',
            interpretation: '值得推进。',
            health_assessment: '建议推进',
          },
        },
        battlefields: [],
        pain_points: [
          {
            title: '回款慢',
            user_voices: ['到账太慢'],
            data_impression: '重复出现',
            interpretation: '现金流压力大。',
          },
        ],
        drivers: [],
        opportunities: [],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.9,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 100,
      },
      overview: {
        sentiment: { positive: 10, negative: 10, neutral: 80 },
        top_communities: [],
        total_communities: 0,
      },
      stats: {
        total_mentions: 0,
        positive_mentions: 0,
        negative_mentions: 0,
        neutral_mentions: 0,
      },
      sources: {
        communities: ['r/stripe'],
        posts_analyzed: 16,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'A_full',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 0,
          key_insights: 0,
          top_opportunity: 'test',
        },
        pain_points: [
          {
            description: '回款慢',
            frequency: 1,
            sentiment_score: -0.4,
            severity: 'high',
            example_posts: [
              {
                community: 'r/stripe',
                content: '回款状态显示已支付，但钱还没到账。',
                permalink: '/r/stripe/comments/demo/payment-delay/',
              },
            ],
            user_examples: ['回款状态显示已支付，但钱还没到账。'],
          },
        ],
        competitors: [],
        opportunities: [],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      report_structured: null,
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.click(
      await screen.findByRole('button', { name: '逐维探索' })
    );
    const painDimensionButton = await screen.findByText('用户痛点洞察');
    await userEvent.click(
      painDimensionButton.closest('button') as HTMLButtonElement
    );

    const link = await screen.findByRole('link', {
      name: /社区：r\/stripe.*回款状态显示已支付/,
    });
    expect(link).toHaveAttribute(
      'href',
      'https://www.reddit.com/r/stripe/comments/demo/payment-delay/'
    );
  });

  it('应该让完整报告和卡片使用同一份 structured 内容，并保留可点击证据链', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: 'report-structured-1',
      status: 'completed',
      generated_at: '2023-01-01',
      product_description: 'PayPal 费用与回款诊断',
      report_markdown:
        '# 报告\n\n## 1. 开篇概览\n这是一份旧的 markdown 文本，不应成为前端完整报告的主来源。\n\n## 2. 决策风向标\n**需求趋势**\n继续看。',
      canonical_report_json: {
        decision_cards: [
          {
            title: '需求趋势',
            conclusion: 'PayPal 费用和回款问题仍在持续出现',
            details: ['跨境卖家反复提到手续费和冻结'],
          },
        ],
        market_health: {
          competition_saturation: {
            level: '中等饱和',
            details: ['核心抱怨集中'],
            interpretation: '还有切低费替代的空间。',
          },
          ps_ratio: {
            ratio: '0.30',
            conclusion: '问题多于解法',
            interpretation: '用户仍在找更稳的替代。',
            health_assessment: '进场信号：强烈建议',
          },
        },
        battlefields: [
          {
            name: '战场：r/stripe',
            subreddits: ['r/stripe'],
            profile: '跨境卖家会在这里集中讨论 payout 失败和冻结问题。',
            pain_points: ['PayPal交付后逆转扣款'],
            strategy_advice:
              '优先切入 payout、手续费和冻结三类反复出现的摩擦。',
          },
        ],
        pain_points: [
          {
            title: 'PayPal交付后逆转扣款',
            user_voices: [
              '围绕「PayPal交付后逆转扣款」的抱怨在本轮样本里反复出现。',
            ],
            data_impression: '重复出现',
            interpretation: '卖家最怕货发了钱又被拿回去。',
          },
        ],
        drivers: [
          { title: '少冻结少扯皮', description: '用户愿意为资金确定性买单。' },
        ],
        opportunities: [
          {
            title: '国际收款开通诊断',
            target_communities: ['r/stripe'],
            target_pain_points: ['国际收款开通受阻'],
            product_positioning: '先帮卖家判断问题卡在银行侧还是平台侧。',
            core_selling_points: ['开通状态一键查 + 少走银行冤枉路'],
          },
        ],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.9,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 100,
      },
      overview: {
        sentiment: { positive: 10, negative: 10, neutral: 80 },
        top_communities: [],
        total_communities: 0,
      },
      stats: {
        total_mentions: 0,
        positive_mentions: 0,
        negative_mentions: 0,
        neutral_mentions: 0,
      },
      sources: {
        communities: ['r/stripe'],
        posts_analyzed: 16,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'A_full',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 0,
          key_insights: 0,
          top_opportunity: 'test',
        },
        pain_points: [
          {
            description: 'PayPal交付后逆转扣款',
            frequency: 1,
            sentiment_score: -0.4,
            severity: 'high',
            example_posts: [
              {
                community: 'r/stripe',
                content: '客户收货后又被 PayPal 逆转扣款，钱直接没了。',
                permalink: '/r/stripe/comments/demo/reversal/',
              },
            ],
            user_examples: ['客户收货后又被 PayPal 逆转扣款，钱直接没了。'],
          },
        ],
        competitors: [],
        opportunities: [],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      report_structured: null,
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/report-structured-1']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.click(
      await screen.findByRole('button', { name: '看完整报告' })
    );

    expect(
      await screen.findByText('和卡片同一颗粒度的完整正文')
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('PayPal 费用和回款问题仍在持续出现').length
    ).toBeGreaterThan(0);
    expect(
      screen.queryByText(
        '这是一份旧的 markdown 文本，不应成为前端完整报告的主来源。'
      )
    ).not.toBeInTheDocument();

    const evidenceLink = screen.getByRole('link', {
      name: /r\/stripe · 去 Reddit 看原帖.*客户收货后又被 PayPal 逆转扣款/,
    });
    expect(evidenceLink).toHaveAttribute(
      'href',
      'https://www.reddit.com/r/stripe/comments/demo/reversal/'
    );
  });

  it('应该按痛点语义对齐证据链，而不是按数组位置硬绑定', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: 'semantic-evidence-1',
      status: 'completed',
      generated_at: '2023-01-01',
      report_markdown: '# 报告',
      canonical_report_json: {
        decision_cards: [
          {
            title: '需求趋势',
            conclusion: '结论清楚',
            details: ['样本够用', '方向明确'],
          },
        ],
        market_health: {
          competition_saturation: {
            level: '中等',
            details: ['讨论稳定', '需求明确'],
            interpretation: '还有切口。',
          },
          ps_ratio: {
            ratio: '0.6',
            conclusion: '痛点多于解法',
            interpretation: '值得推进。',
            health_assessment: '进场信号：强烈建议',
          },
        },
        battlefields: [],
        pain_points: [
          {
            title: '平台合规资料卡壳，开通流程反复被打回',
            user_voices: ['地址和资料填完了，审核还是反复卡住。'],
            data_impression: '重复出现',
            interpretation: '资料审核会直接拖慢开通。',
          },
          {
            title: '退款后手续费照扣，利润被一点点吃掉',
            user_voices: ['退一单就先亏一笔手续费。'],
            data_impression: '重复出现',
            interpretation: '退款成本会直接吃利润。',
          },
        ],
        drivers: [],
        opportunities: [],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.9,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 100,
      },
      overview: {
        sentiment: { positive: 10, negative: 10, neutral: 80 },
        top_communities: [],
        total_communities: 0,
      },
      stats: {
        total_mentions: 0,
        positive_mentions: 0,
        negative_mentions: 0,
        neutral_mentions: 0,
      },
      sources: {
        communities: ['r/stripe'],
        posts_analyzed: 16,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'A_full',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 0,
          key_insights: 0,
          top_opportunity: 'test',
        },
        pain_points: [
          {
            description: '退款后手续费照扣，利润被一点点吃掉',
            frequency: 1,
            sentiment_score: -0.4,
            severity: 'high',
            example_posts: [
              {
                community: 'r/stripe',
                content: '退一单就先亏一笔手续费，利润一下就薄了。',
                permalink: '/r/stripe/comments/demo/refund-fee/',
              },
            ],
            user_examples: ['退一单就先亏一笔手续费，利润一下就薄了。'],
          },
          {
            description: '平台合规资料卡壳，开通流程反复被打回',
            frequency: 1,
            sentiment_score: -0.4,
            severity: 'high',
            example_posts: [
              {
                community: 'r/stripe',
                content: '地址和资料填完了，审核还是反复卡住。',
                permalink: '/r/stripe/comments/demo/address-review/',
              },
            ],
            user_examples: ['地址和资料填完了，审核还是反复卡住。'],
          },
        ],
        competitors: [],
        opportunities: [],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      report_structured: null,
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/semantic-evidence-1']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.click(
      await screen.findByRole('button', { name: '看完整报告' })
    );

    const alignedLink = await screen.findByRole('link', {
      name: /r\/stripe · 去 Reddit 看原帖.*地址和资料填完了，审核还是反复卡住/,
    });
    expect(alignedLink).toHaveAttribute(
      'href',
      'https://www.reddit.com/r/stripe/comments/demo/address-review/'
    );
  });

  it('应该在报告失败时给出统一错误状态和下一步动作', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockRejectedValue(
      new Error('服务暂时不可用')
    );
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole('heading', {
        name: '这份结果还在整理中',
        level: 3,
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText('这份报告刚才没整理完整，先重新加载一次。')
    ).toBeInTheDocument();
    expect(
      screen.getByText('先重载一次；还不行就回首页重跑。')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: '重新加载' })
    ).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '返回首页' })).toHaveLength(2);
    expect(screen.queryByText('服务暂时不可用')).not.toBeInTheDocument();
  });

  it('应该把弱结果主 CTA 带回输入页并恢复原描述', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: '123',
      status: 'completed',
      generated_at: '2023-01-01',
      product_description:
        '帮跨境卖家把平台手续费、回款周期和退款损耗统一看清楚的利润追踪工具。',
      canonical_report_json: {
        decision_cards: [
          {
            title: '需求趋势',
            conclusion: '方向已经冒头',
            details: ['样本还不够大', '值得继续放大'],
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
        pain_points: [],
        drivers: [],
        opportunities: [],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.66,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 100,
      },
      overview: {
        sentiment: { positive: 10, negative: 10, neutral: 80 },
        top_communities: [],
        total_communities: 0,
      },
      stats: {
        total_mentions: 0,
        positive_mentions: 0,
        negative_mentions: 0,
        neutral_mentions: 0,
      },
      sources: {
        communities: ['r/startups'],
        posts_analyzed: 8,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'B_trimmed',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 0,
          key_insights: 0,
          top_opportunity: 'test',
        },
        pain_points: [],
        competitors: [],
        opportunities: [],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      report_structured: null,
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
          <Route path="/" element={<InputPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('先定值不值得追')).toBeInTheDocument();
    expect(screen.getByText('这轮先拍小板')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '支持拍板的 3 条证据', level: 2 })
    ).toBeInTheDocument();
    expect(
      screen.getByText('先把最能支撑拍板的三条信号看完。')
    ).toBeInTheDocument();
    expect(
      (await screen.findAllByRole('button', { name: '放大范围再跑' })).length
    ).toBeGreaterThan(0);
    screen.getAllByRole('button', { name: '放大范围再跑' })[0]!.click();

    expect(await screen.findByText('已带回这次分析方向')).toBeInTheDocument();
    expect(
      screen.getByText('已带回你刚才看的方向。先改成更贴近用户原话，再重跑。')
    ).toBeInTheDocument();
    expect(
      (
        screen.getByRole('textbox', {
          name: /产品描述/i,
        }) as HTMLTextAreaElement
      ).value
    ).toContain('帮跨境卖家把平台手续费');
  });

  it('应该把 X_blocked 清晰展示为线索态而不是方向拍板态', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: 'x-blocked-1',
      status: 'completed',
      generated_at: '2023-01-01',
      product_description: '自由输入测试',
      canonical_report_json: {
        decision_cards: [],
        market_health: {
          competition_saturation: {
            level: '早期',
            details: ['线索还不够硬'],
            interpretation: '先扩样本',
          },
          ps_ratio: {
            ratio: 'N/A',
            conclusion: '样本偏轻',
            interpretation: '先看线索',
            health_assessment: '继续观察',
          },
        },
        battlefields: [],
        pain_points: [],
        drivers: [],
        opportunities: [],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.12,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 20,
      },
      overview: {
        sentiment: { positive: 1, negative: 1, neutral: 18 },
        top_communities: [
          { name: 'r/EDC', mention_count: 12, sentiment_score: 0.4 },
        ],
        total_communities: 1,
      },
      stats: {
        total_mentions: 20,
        positive_mentions: 1,
        negative_mentions: 1,
        neutral_mentions: 18,
      },
      sources: {
        communities: ['r/EDC'],
        posts_analyzed: 20,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'X_blocked',
        analysis_blocked: 'quality_gate_blocked',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 1,
          key_insights: 1,
          top_opportunity: '',
        },
        pain_points: [],
        competitors: [],
        opportunities: [],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      report_structured: null,
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/x-blocked-1']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole('heading', {
        name: '这次先看已抓到的线索',
        level: 2,
      })
    ).toBeInTheDocument();
    expect(screen.getByText('先把它当成方向线索')).toBeInTheDocument();
    expect(screen.getByText('系统正在补证据')).toBeInTheDocument();
  });

  it('应该在 canonical_report_json 缺失时暴露统一缺口，而不是前端自拼报告', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: '123',
      status: 'completed',
      generated_at: '2023-01-01',
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.9,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 100,
      },
      overview: {
        sentiment: { positive: 10, negative: 10, neutral: 80 },
        top_communities: [],
        total_communities: 0,
      },
      stats: {
        total_mentions: 0,
        positive_mentions: 0,
        negative_mentions: 0,
        neutral_mentions: 0,
      },
      report_html: '<html></html>',
      sources: {
        communities: ['r/startups'],
        posts_analyzed: 16,
        cache_hit_rate: 0,
        analysis_duration_seconds: 10,
        reddit_api_calls: 1,
        data_source: 'real',
        report_tier: 'A_full',
        structured_llm_status: 'completed',
      },
      report: {
        executive_summary: {
          total_communities: 0,
          key_insights: 0,
          top_opportunity: 'test',
        },
        pain_points: [],
        competitors: [],
        opportunities: [],
        entity_summary: { brands: [], features: [], pain_points: [] },
        action_items: [],
      },
      canonical_report_json: null,
      report_structured: null,
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole('heading', {
        name: '这份结果还在整理中',
        level: 3,
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText('这份报告还在整理中，先重新加载一次。')
    ).toBeInTheDocument();
  });
});
