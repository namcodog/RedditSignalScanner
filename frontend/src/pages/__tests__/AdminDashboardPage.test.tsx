import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import AdminDashboardPage from '../AdminDashboardPage';
import * as adminApi from '@/api/admin.api';

vi.mock('@/api/admin.api', () => ({
  getAdminDashboardStats: vi.fn(),
  getRecentTasks: vi.fn(),
}));

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(adminApi.getAdminDashboardStats).mockResolvedValue({
      total_users: 12,
      total_tasks: 34,
      tasks_today: 3,
      tasks_completed_today: 2,
      avg_processing_time: 18.5,
      cache_hit_rate: 0.72,
      active_workers: 2,
      pipeline_health: {},
    });
    vi.mocked(adminApi.getRecentTasks).mockResolvedValue({
      items: [
        {
          task_id: 'task-12345678',
          user_email: 'admin@example.com',
          status: 'completed',
          created_at: '2025-10-25T08:00:00Z',
          completed_at: '2025-10-25T08:01:00Z',
          processing_seconds: 60,
          confidence_score: 0.88,
          analysis_version: 1,
          posts_analyzed: 16,
          cache_hit_rate: 0.5,
          communities_count: 3,
          reddit_api_calls: 4,
          pain_points_count: 2,
          competitors_count: 1,
          opportunities_count: 1,
        },
      ],
      total: 1,
    });
  });

  it('应该显示当前 admin 仪表盘核心统计和最近任务', async () => {
    render(
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '系统控制面', level: 1 })).toBeInTheDocument();
    });

    expect(screen.getByRole('heading', { name: '今天可以放心开工', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('这里不回答市场值不值，只回答今天这套机器能不能放心开工。')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '今天先看什么', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '今天机器稳不稳', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '控制面捷径', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '今天先做哪一步', level: 3 })).toBeInTheDocument();
    expect(screen.getByText('当前风险级别')).toBeInTheDocument();
    expect(screen.getByText('低风险')).toBeInTheDocument();
    expect(screen.getByText('队列压力（最近任务）')).toBeInTheDocument();
    expect(screen.getByText('空闲')).toBeInTheDocument();
    expect(screen.getByText('今日建议动作')).toBeInTheDocument();
    expect(screen.getByText('机器状态稳定，可以按计划开新任务，异常时再回控制面复核。')).toBeInTheDocument();
    expect(screen.getByText('先抽查已完成任务（1 条）')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '先看任务账本' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '再看社区池' })).toBeInTheDocument();
    expect(screen.getAllByText('12').length).toBeGreaterThan(0);
    expect(screen.getAllByText('34').length).toBeGreaterThan(0);
    expect(screen.getAllByText('18.5秒').length).toBeGreaterThan(0);
    expect(screen.getAllByText('72.0%').length).toBeGreaterThan(0);
    expect(document.body.textContent).toContain('任务 task-123...');
    expect(screen.getByText('16 帖子')).toBeInTheDocument();
  });

  it('应该调用 admin.api 作为唯一数据来源', async () => {
    render(
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(adminApi.getAdminDashboardStats).toHaveBeenCalled();
      expect(adminApi.getRecentTasks).toHaveBeenCalledWith({ limit: 5 });
    });
  });

  it('应该在最近任务为空时给出统一空状态和下一步动作', async () => {
    vi.mocked(adminApi.getRecentTasks).mockResolvedValue({
      items: [],
      total: 0,
    });

    render(
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '当前还没有最近任务', level: 3 })).toBeInTheDocument();
    });

    expect(screen.getByText('这不代表系统坏了，只是最近没有新的分析任务进来，或者这批任务还没开始跑。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '看任务账本' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '看社区池' })).toBeInTheDocument();
  });

  it('应该在仪表盘失败时给出统一错误状态和下一步动作', async () => {
    vi.mocked(adminApi.getAdminDashboardStats).mockRejectedValue(new Error('后台统计服务不可用'));

    render(
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '系统驾驶舱暂时没拿到最新状态', level: 3 })).toBeInTheDocument();
    });

    expect(screen.getByText('后台统计服务不可用')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '刷新仪表盘' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '看任务账本' })).toBeInTheDocument();
  });
});
