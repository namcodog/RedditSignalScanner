import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import TaskLedgerPage from '@/pages/admin/TaskLedgerPage';
import * as adminApi from '@/api/admin.api';

vi.mock('@/api/admin.api', () => ({
  getRecentTasks: vi.fn(),
  getTaskLedger: vi.fn(),
}));

describe('TaskLedgerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(adminApi.getRecentTasks).mockResolvedValue({
      items: [
        {
          task_id: '11111111-1111-1111-1111-111111111111',
          user_email: 'admin@example.com',
          status: 'completed',
          created_at: '2025-12-29T00:00:00Z',
          completed_at: '2025-12-29T00:01:00Z',
          processing_seconds: 60,
          confidence_score: 0.9,
          analysis_version: 1,
          posts_analyzed: 12,
          cache_hit_rate: 0.6,
          communities_count: 2,
          reddit_api_calls: 3,
          pain_points_count: 2,
          competitors_count: 1,
          opportunities_count: 1,
        },
      ],
      total: 1,
    });
    vi.mocked(adminApi.getTaskLedger).mockResolvedValue({
      task: {
        id: '11111111-1111-1111-1111-111111111111',
        user_id: '22222222-2222-2222-2222-222222222222',
        status: 'completed',
        product_description: 'test desc',
        created_at: '2025-12-29T00:00:00Z',
        completed_at: '2025-12-29T00:01:00Z',
      },
      analysis: {
        id: '33333333-3333-3333-3333-333333333333',
        task_id: '11111111-1111-1111-1111-111111111111',
        analysis_version: 1,
        confidence_score: null,
        sources: {
          report_tier: 'B_trimmed',
          facts_v2_quality: {
            tier: 'B_trimmed',
            flags: ['comments_not_used'],
          },
        },
        created_at: '2025-12-29T00:00:00Z',
      },
      facts_snapshot: {
        id: '44444444-4444-4444-4444-444444444444',
        tier: 'B_trimmed',
        status: 'ok',
        quality: 'good',
      },
    } as any);
  });

  it('应该通过 admin.api 拉取账本列表和详情', async () => {
    render(
      <MemoryRouter>
        <TaskLedgerPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(adminApi.getRecentTasks).toHaveBeenCalledWith({ limit: 50, offset: 0 });
    });

    fireEvent.click(screen.getByText('admin@example.com'));

    await waitFor(() => {
      expect(adminApi.getTaskLedger).toHaveBeenCalledWith(
        '11111111-1111-1111-1111-111111111111',
        true,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('任务报告')).toBeInTheDocument();
      expect(screen.getByText('B_trimmed')).toBeInTheDocument();
      expect(screen.getByText(/comments_not_used/)).toBeInTheDocument();
    });
  });
});
