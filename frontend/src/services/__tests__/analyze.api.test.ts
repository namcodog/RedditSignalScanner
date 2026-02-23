import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as analyzeApi from '../../api/analyze.api';
import * as client from '../../api/client';
import type { ReportResponse } from '@/types';

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  }
}));

const createMockReport = (taskId: string): ReportResponse => ({
  task_id: taskId,
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
});

describe('analyze.api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createAnalyzeTask', () => {
    it('calls POST /api/analyze', async () => {
      vi.mocked(client.apiClient.post).mockResolvedValue({ data: { task_id: 't1' } } as any);
      
      await analyzeApi.createAnalyzeTask({ product_description: 'desc' });
      
      expect(client.apiClient.post).toHaveBeenCalledWith(
        '/analyze',
        { product_description: 'desc' }
      );
    });
  });

  describe('getAnalysisReport', () => {
    it('calls GET /api/report/:id', async () => {
      const report = createMockReport('t1');
      vi.mocked(client.apiClient.get).mockResolvedValue({ data: report } as any);

      await analyzeApi.getAnalysisReport('t1');

      expect(client.apiClient.get).toHaveBeenCalledWith('/report/t1');
    });
  });
});