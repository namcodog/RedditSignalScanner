import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TaskLedgerPage from '@/pages/admin/TaskLedgerPage';
import * as adminServiceModule from '@/services/admin.service';

vi.mock('@/services/admin.service', () => ({
  adminService: {
    getTaskLedger: vi.fn(),
  },
}));

describe('TaskLedgerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('能输入 task_id 并拉取 ledger', async () => {
    vi.mocked(adminServiceModule.adminService.getTaskLedger).mockResolvedValue({
      task: {
        id: '11111111-1111-1111-1111-111111111111',
        user_id: '22222222-2222-2222-2222-222222222222',
        status: 'completed',
        mode: 'market_insight',
        audit_level: 'lab',
        topic_profile_id: 'shopify_ads_conversion_v1',
        product_description: 'test desc',
        retry_count: 0,
        failure_category: null,
        created_at: '2025-12-29T00:00:00Z',
        updated_at: '2025-12-29T00:00:00Z',
        completed_at: '2025-12-29T00:00:00Z',
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
        task_id: '11111111-1111-1111-1111-111111111111',
        schema_version: '2.0',
        tier: 'B_trimmed',
        passed: true,
        audit_level: 'lab',
        status: 'ok',
        validator_level: 'info',
        retention_days: 30,
        expires_at: null,
        error_code: null,
        quality: {
          tier: 'B_trimmed',
          flags: ['comments_not_used'],
          passed: true,
        } as any,
        created_at: '2025-12-29T00:00:00Z',
      },
    });

    render(
      <MemoryRouter>
        <TaskLedgerPage />
      </MemoryRouter>
    );

    expect(screen.getByText('任务复盘')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('输入 task_id（UUID）');
    fireEvent.change(input, { target: { value: '11111111-1111-1111-1111-111111111111' } });
    fireEvent.click(screen.getByText('查询'));

    await waitFor(() => {
      expect(adminServiceModule.adminService.getTaskLedger).toHaveBeenCalledWith(
        '11111111-1111-1111-1111-111111111111',
        { includePackage: false }
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('ledger-report-tier').textContent).toContain('B_trimmed');
      expect(screen.getByTestId('ledger-flags').textContent).toContain('comments_not_used');
    });
  });
});
