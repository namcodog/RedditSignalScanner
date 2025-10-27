/**
 * AdminDashboardPage 测试 - 简化版
 * 测试目标: 覆盖率 >80%
 * 注意: AdminDashboardPage使用Mock数据，不调用API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminDashboardPage from '../AdminDashboardPage';
import * as adminService from '@/services/admin.service';

// Mock admin service
vi.mock('@/services/admin.service', () => ({
  adminService: {
    getCommunities: vi.fn(),
    getAnalysisTasks: vi.fn(),
    getBetaFeedback: vi.fn(),
    getQualityMetrics: vi.fn(),
  },
}));

const mockCommunities = {
  items: [
    {
      community: 'r/startups',
      hit_7d: 12,
      last_crawled_at: '2025-10-26T10:00:00Z',
      dup_ratio: 0.05,
      spam_ratio: 0.02,
      topic_score: 0.85,
      c_score: 0.90,
      status_color: 'green' as const,
      labels: ['startup', 'funding'],
      evidence_samples: ['Sample evidence 1'],
    },
    {
      community: 'r/technology',
      hit_7d: 5,
      last_crawled_at: '2025-10-25T10:00:00Z',
      dup_ratio: 0.10,
      spam_ratio: 0.05,
      topic_score: 0.70,
      c_score: 0.75,
      status_color: 'yellow' as const,
      labels: ['tech', 'innovation'],
      evidence_samples: ['Sample evidence 2'],
    },
    {
      community: 'r/programming',
      hit_7d: 2,
      last_crawled_at: '2025-10-24T10:00:00Z',
      dup_ratio: 0.15,
      spam_ratio: 0.08,
      topic_score: 0.50,
      c_score: 0.55,
      status_color: 'red' as const,
      labels: ['code', 'dev'],
      evidence_samples: ['Sample evidence 3'],
    },
  ],
  total: 3,
  page: 1,
  page_size: 200,
};

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    // Setup default mock implementation
    vi.mocked(adminService.adminService.getCommunities).mockResolvedValue(mockCommunities);
    vi.mocked(adminService.adminService.getAnalysisTasks).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  });

  it('应该显示页面标题', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    expect(screen.getByText('Reddit Signal Scanner')).toBeInTheDocument();
    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
  });

  it('应该显示Tab导航', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    expect(screen.getByText('社区验收')).toBeInTheDocument();
    expect(screen.getByText('算法验收')).toBeInTheDocument();
    expect(screen.getByText('用户反馈')).toBeInTheDocument();
  });

  it('应该默认显示社区验收Tab', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('社区名')).toBeInTheDocument();
      expect(screen.getByText('7天命中')).toBeInTheDocument();
    });
  });

  it('应该能切换Tab', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待初始数据加载
    await waitFor(() => {
      expect(screen.getByText('社区名')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('算法验收'));
    // 算法验收Tab显示"暂无分析任务数据"（因为没有mock数据）
    await waitFor(() => {
      expect(screen.getByText(/暂无分析任务数据/i)).toBeInTheDocument();
    });
  });

  it('应该显示Mock社区数据', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
      expect(screen.getByText('r/technology')).toBeInTheDocument();
    });
  });

  it('应该显示状态标签', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待数据加载后再检查状态标签
    await waitFor(() => {
      // 使用getAllByText因为状态标签和筛选器都有这些文本
      expect(screen.getAllByText('正常').length).toBeGreaterThan(0);
      expect(screen.getAllByText('警告').length).toBeGreaterThan(0);
      expect(screen.getAllByText('异常').length).toBeGreaterThan(0);
    });
  });

  it('应该有搜索功能', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText(/搜索/i) as HTMLInputElement;
    fireEvent.change(searchInput, { target: { value: 'startups' } });
    expect(searchInput.value).toBe('startups');
  });

  it('应该能过滤社区', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
      expect(screen.getByText('r/technology')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText(/搜索/i);
    fireEvent.change(searchInput, { target: { value: 'startups' } });
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
      expect(screen.queryByText('r/technology')).not.toBeInTheDocument();
    });
  });

  it('应该有状态筛选器', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
    });
    const [statusSelect] = screen.getAllByRole<HTMLSelectElement>('combobox');
    expect(statusSelect).toBeDefined();
    if (!statusSelect) {
      throw new Error('状态筛选器未找到');
    }
  });

  it('应该能按状态筛选', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
      expect(screen.getByText('r/technology')).toBeInTheDocument();
    });
    const [statusSelect] = screen.getAllByRole<HTMLSelectElement>('combobox');
    if (!statusSelect) {
      throw new Error('状态筛选器未找到');
    }
    fireEvent.change(statusSelect, { target: { value: 'green' } });
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
      expect(screen.queryByText('r/technology')).not.toBeInTheDocument();
    });
  });

  it('应该显示功能按钮', async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('r/startups')).toBeInTheDocument();
    });
    expect(screen.getByText(/生成.*Patch/i)).toBeInTheDocument();
    expect(screen.getByText(/一键开.*PR/i)).toBeInTheDocument();
  });
});
