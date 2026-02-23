import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReportPage from '../ReportPage';
import * as analyzeApiModule from '@/api/analyze.api';

// Mock API
vi.mock('@/api/analyze.api', () => ({
  getAnalysisReport: vi.fn(),
  getTaskSources: vi.fn(),
}));

describe('ReportPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
        opportunities: [],
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
    
    // Structured summary should appear in decision cards
    expect(await screen.findByText('讨论热度持续稳定')).toBeInTheDocument();
  });
});
