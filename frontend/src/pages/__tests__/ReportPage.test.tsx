import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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
      () => new Promise(() => undefined) as any,
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
    expect(screen.getByText('先帮你把市场温度、用户抱怨和可追机会捞出来，马上就能进正式判断。')).toBeInTheDocument();
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
      report_structured: {
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
            product_positioning: '一键抓 Amazon/Etsy/Shopify/TikTok 回款，费率透明不漏扣',
            core_selling_points: [],
          },
        ],
      },
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
    expect(screen.getByRole('heading', { name: '这次已经值得继续做', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('可直接看结论')).toBeInTheDocument();
    expect(screen.getByText('先拍第一板')).toBeInTheDocument();
    expect(screen.getByText('现在建议')).toBeInTheDocument();
    expect(screen.getByText('可以拍第一板')).toBeInTheDocument();
    expect(screen.getByText('拍板依据')).toBeInTheDocument();
    expect(screen.getAllByText(/一键抓 Amazon\/Etsy\/Shopify\/TikTok 回款/).length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: '支持拍板的 3 条证据', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('先扫这三条就够；不够再往下拆。')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '逐维探索' })).toHaveLength(1);
    expect(screen.getAllByRole('button', { name: '看完整报告' })).toHaveLength(1);
    expect(screen.getByRole('heading', { name: '如果还想继续，再往下看', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('先挑最影响拍板的一块看。')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '市场洞察报告已生成', level: 1 })).not.toBeInTheDocument();
  });

  it('应该在报告失败时给出统一错误状态和下一步动作', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockRejectedValue(new Error('服务暂时不可用'));
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/123']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: '这份结果还在整理中', level: 3 })).toBeInTheDocument();
    expect(screen.getByText('系统刚才没整理完整，先重新加载一次。')).toBeInTheDocument();
    expect(screen.getByText('先重载一次；还不行就回首页重跑。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '返回首页' })).toHaveLength(2);
    expect(screen.queryByText('服务暂时不可用')).not.toBeInTheDocument();
  });

  it('应该把弱结果主 CTA 带回输入页并恢复原描述', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: '123',
      status: 'completed',
      generated_at: '2023-01-01',
      product_description: '帮跨境卖家把平台手续费、回款周期和退款损耗统一看清楚的利润追踪工具。',
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
      report_structured: {
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
    expect(screen.getByRole('heading', { name: '支持拍板的 3 条证据', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('先扫这三条就够；不够再往下拆。')).toBeInTheDocument();
    expect((await screen.findAllByRole('button', { name: '放大范围再跑' })).length).toBeGreaterThan(0);
    screen.getAllByRole('button', { name: '放大范围再跑' })[0]!.click();

    expect(await screen.findByText('已带回这次分析方向')).toBeInTheDocument();
    expect(screen.getByText('已带回你刚才看的方向。先改成更贴近用户原话，再重跑。')).toBeInTheDocument();
    expect((screen.getByRole('textbox', { name: /产品描述/i }) as HTMLTextAreaElement).value).toContain('帮跨境卖家把平台手续费');
  });

  it('应该把 X_blocked 清晰展示为线索态而不是方向拍板态', async () => {
    vi.mocked(analyzeApiModule.getAnalysisReport).mockResolvedValue({
      task_id: 'x-blocked-1',
      status: 'completed',
      generated_at: '2023-01-01',
      product_description: '自由输入测试',
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.12,
        processing_time_seconds: 10,
        cache_hit_rate: 0,
        total_mentions: 20,
      },
      overview: {
        sentiment: { positive: 1, negative: 1, neutral: 18 },
        top_communities: [{ name: 'r/EDC', mention_count: 12, sentiment_score: 0.4 }],
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
      report_structured: {
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
    } as any);
    vi.mocked(analyzeApiModule.getTaskSources).mockResolvedValue(null as any);

    render(
      <MemoryRouter initialEntries={['/report/x-blocked-1']}>
        <Routes>
          <Route path="/report/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: '这次先看已抓到的线索', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('先把它当成方向线索')).toBeInTheDocument();
    expect(screen.getByText('系统正在补证据')).toBeInTheDocument();
  });
});
