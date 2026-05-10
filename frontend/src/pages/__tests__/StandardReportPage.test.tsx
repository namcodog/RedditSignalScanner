import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import StandardReportPage from '../StandardReportPage';

const mockFetch = vi.fn();
const mockNavigate = vi.fn();

vi.stubGlobal('fetch', mockFetch);

vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>(
      'react-router-dom'
    );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

afterEach(() => {
  mockFetch.mockReset();
  mockNavigate.mockReset();
});

describe('StandardReportPage', () => {
  it('renders fixed snapshot cards and full report from the same payload', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            slug: 'edc-pocket-organizer',
            title: '户外',
            prompt: 'EDC 标准报告',
            topic_profile_id: 'edc_everyday_carry_v1',
            task_id: 'task-1',
            validated_at: '2026-03-20T16:49:55.096303+00:00',
            summary: {
              battlefields: 4,
              pain_points: 3,
              drivers: 3,
              opportunities: 2,
            },
            snapshot_url: '/topic-profile-reports/edc-pocket-organizer.json',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          slug: 'edc-pocket-organizer',
          title: '户外',
          prompt: 'EDC 标准报告',
          topic_profile_id: 'edc_everyday_carry_v1',
          task_id: 'task-1',
          validated_at: '2026-03-20T16:49:55.096303+00:00',
          summary: {
            battlefields: 4,
            pain_points: 3,
            drivers: 3,
            opportunities: 2,
          },
          report: {
            task_id: 'task-1',
            status: 'completed',
            generated_at: '2026-03-20T16:49:55.096303+00:00',
            product_description: 'EDC 标准报告',
            report_markdown:
              '# 户外 · 市场洞察报告\n\n## 1. 开篇概览\n这是一份先讲结论再讲证据的标准报告。\n\n## 2. 决策风向标\n**需求趋势**\n讨论密集。\n\n## 3. 概览（市场健康度诊断）\n可继续推进。',
            report_html: '<h2>完整报告正文</h2>',
            canonical_report_json: {
              decision_cards: [
                {
                  title: '需求趋势',
                  conclusion: '值得继续看',
                  details: ['讨论密集', '抱怨重复'],
                },
                {
                  title: '问题/解决方案比',
                  conclusion: '问题多于解法',
                  details: ['P/S 比低'],
                },
                {
                  title: '高潜力社群',
                  conclusion: '社区集中',
                  details: ['r/EDC 很集中'],
                },
                {
                  title: '明确机会点',
                  conclusion: '机会已经出现',
                  details: ['可以先做收纳验证'],
                },
              ],
              market_health: {
                competition_saturation: {
                  level: '有空间',
                  details: ['社区集中', '讨论持续'],
                  interpretation: '还能切进去',
                },
                ps_ratio: {
                  ratio: '0.30',
                  conclusion: '问题多于解法',
                  interpretation: '机会还在',
                  health_assessment: '可继续推进',
                },
              },
              battlefields: [
                {
                  name: '战场：r/EDC',
                  subreddits: ['r/EDC'],
                  profile: '用户在找更顺手的收纳。',
                  pain_points: ['拿取不顺'],
                  strategy_advice: '先做收纳验证。',
                },
              ],
              pain_points: [
                {
                  title: '口袋容易乱',
                  user_voices: ['钥匙卡耳机总打架', '掏东西慢'],
                  data_impression: '重复出现',
                  interpretation: '收纳结构没解决拿取顺序。',
                },
              ],
              drivers: [
                {
                  title: '拿取顺手',
                  description: '每天都用，愿意为顺手买单。',
                },
              ],
              opportunities: [
                {
                  title: 'EDC 收纳夹层',
                  target_pain_points: ['口袋容易乱'],
                  target_communities: ['r/EDC'],
                  product_positioning: '让钥匙卡耳机分层归位。',
                  core_selling_points: [
                    '分层收纳 + 更快拿取',
                    '减少硌口袋 + 更稳固',
                  ],
                },
              ],
            },
            report: {
              executive_summary: {},
              pain_points: [
                {
                  description: '口袋容易乱',
                  frequency: 2,
                  sentiment_score: -0.4,
                  severity: 'medium',
                  example_posts: [
                    {
                      community: 'r/EDC',
                      content: '我的门禁卡和钥匙总是缠在一起，掏出来很慢。',
                      permalink: '/r/EDC/comments/demo/example/',
                    },
                  ],
                  user_examples: ['我的门禁卡和钥匙总是缠在一起，掏出来很慢。'],
                },
              ],
              competitors: [],
              opportunities: [],
              entity_summary: {},
              action_items: [],
            },
            metadata: { confidence_score: 0.9, llm_used: true },
            overview: { top_communities: [] },
            stats: {
              total_posts: 0,
              total_comments: 0,
              opportunity_score: 0,
              pain_point_count: 0,
            },
            sources: { report_tier: 'A_full' },
          },
        }),
      });

    render(
      <MemoryRouter
        initialEntries={['/standard-report/edc-pocket-organizer?view=cards']}
      >
        <Routes>
          <Route
            path="/standard-report/:slug"
            element={<StandardReportPage />}
          />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('固定标准结果')).toBeInTheDocument();
    expect(screen.getByText('1. 开篇概览')).toBeInTheDocument();
    expect(screen.getByText('2. 决策风向标')).toBeInTheDocument();
    expect(screen.getByText('4. 核心战场推荐（画像分级）')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: '解释：什么是战场' })
    ).toBeInTheDocument();
    expect(screen.queryByText('阅读方法')).not.toBeInTheDocument();
    expect(screen.getAllByText('值得继续看').length).toBeGreaterThan(0);
    const evidenceLink = screen.getByRole('link', {
      name: /r\/EDC · 去 Reddit 看原帖.*我的门禁卡和钥匙总是缠在一起/,
    });
    expect(evidenceLink).toHaveAttribute(
      'href',
      'https://www.reddit.com/r/EDC/comments/demo/example/'
    );
    expect(screen.queryByText(/topic_profile:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/task:/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '完整报告' }));

    await waitFor(() => {
      expect(
        screen.getByText('和卡片同一颗粒度的完整正文')
      ).toBeInTheDocument();
    });
    expect(screen.getByText('1. 开篇概览')).toBeInTheDocument();
    expect(screen.queryByText('## 1. 开篇概览')).not.toBeInTheDocument();
    const fullReportEvidenceLink = screen.getByRole('link', {
      name: /r\/EDC · 去 Reddit 看原帖.*我的门禁卡和钥匙总是缠在一起/,
    });
    expect(fullReportEvidenceLink).toHaveAttribute(
      'href',
      'https://www.reddit.com/r/EDC/comments/demo/example/'
    );
  });

  it('can send users back home with a clean input and a light standard-report hint', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            slug: 'edc-pocket-organizer',
            title: '户外',
            prompt: 'EDC 标准报告',
            topic_profile_id: 'edc_everyday_carry_v1',
            task_id: 'task-1',
            validated_at: '2026-03-20T16:49:55.096303+00:00',
            summary: {
              battlefields: 4,
              pain_points: 3,
              drivers: 3,
              opportunities: 2,
            },
            snapshot_url: '/topic-profile-reports/edc-pocket-organizer.json',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          slug: 'edc-pocket-organizer',
          title: '户外',
          prompt: 'EDC 标准报告',
          topic_profile_id: 'edc_everyday_carry_v1',
          task_id: 'task-1',
          validated_at: '2026-03-20T16:49:55.096303+00:00',
          summary: {
            battlefields: 4,
            pain_points: 3,
            drivers: 3,
            opportunities: 2,
          },
          report: {
            task_id: 'task-1',
            status: 'completed',
            generated_at: '2026-03-20T16:49:55.096303+00:00',
            product_description: 'EDC 标准报告',
            report_markdown:
              '# 户外 · 市场洞察报告\n\n## 1. 开篇概览\n这是一份先讲结论再讲证据的标准报告。\n\n## 2. 决策风向标\n**需求趋势**\n讨论密集。\n\n## 3. 概览（市场健康度诊断）\n可继续推进。',
            report_html: '<h2>完整报告正文</h2>',
            canonical_report_json: {
              decision_cards: [
                {
                  title: '需求趋势',
                  conclusion: '值得继续看',
                  details: ['讨论密集', '抱怨重复'],
                },
                {
                  title: '问题/解决方案比',
                  conclusion: '问题多于解法',
                  details: ['P/S 比低'],
                },
                {
                  title: '高潜力社群',
                  conclusion: '社区集中',
                  details: ['r/EDC 很集中'],
                },
                {
                  title: '明确机会点',
                  conclusion: '机会已经出现',
                  details: ['可以先做收纳验证'],
                },
              ],
              market_health: {
                competition_saturation: {
                  level: '有空间',
                  details: ['社区集中', '讨论持续'],
                  interpretation: '还能切进去',
                },
                ps_ratio: {
                  ratio: '0.30',
                  conclusion: '问题多于解法',
                  interpretation: '机会还在',
                  health_assessment: '可继续推进',
                },
              },
              battlefields: [
                {
                  name: '战场：r/EDC',
                  subreddits: ['r/EDC'],
                  profile: '用户在找更顺手的收纳。',
                  pain_points: ['拿取不顺'],
                  strategy_advice: '先做收纳验证。',
                },
              ],
              pain_points: [
                {
                  title: '口袋容易乱',
                  user_voices: ['钥匙卡耳机总打架', '掏东西慢'],
                  data_impression: '重复出现',
                  interpretation: '收纳结构没解决拿取顺序。',
                },
              ],
              drivers: [
                {
                  title: '拿取顺手',
                  description: '每天都用，愿意为顺手买单。',
                },
              ],
              opportunities: [
                {
                  title: 'EDC 收纳夹层',
                  target_pain_points: ['口袋容易乱'],
                  target_communities: ['r/EDC'],
                  product_positioning: '让钥匙卡耳机分层归位。',
                  core_selling_points: [
                    '分层收纳 + 更快拿取',
                    '减少硌口袋 + 更稳固',
                  ],
                },
              ],
            },
            report: {
              executive_summary: {},
              pain_points: [],
              competitors: [],
              opportunities: [],
              entity_summary: {},
              action_items: [],
            },
            metadata: { confidence_score: 0.9, llm_used: true },
            overview: { top_communities: [] },
            stats: {
              total_posts: 0,
              total_comments: 0,
              opportunity_score: 0,
              pain_point_count: 0,
            },
            sources: { report_tier: 'A_full' },
          },
        }),
      });

    render(
      <MemoryRouter
        initialEntries={['/standard-report/edc-pocket-organizer?view=report']}
      >
        <Routes>
          <Route
            path="/standard-report/:slug"
            element={<StandardReportPage />}
          />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('回首页写我的问题')).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole('button', { name: '回首页写我的问题' })
    );

    expect(mockNavigate).toHaveBeenCalledWith('/', {
      state: {
        prefillSource: 'standard-report',
        prefillHint:
          '刚看完这份标准样板。输入框已经清空，直接按你的真实问题重写就行。',
        prefillStandardTitle: '户外',
        prefillPromptSuggestion: 'EDC 标准报告',
      },
    });
  });
});
