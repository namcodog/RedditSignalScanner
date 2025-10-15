/**
 * AdminDashboardPage 测试 - 简化版
 * 测试目标: 覆盖率 >80%
 * 注意: AdminDashboardPage使用Mock数据，不调用API
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminDashboardPage from '../AdminDashboardPage';

describe('AdminDashboardPage', () => {
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

  it('应该默认显示社区验收Tab', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    expect(screen.getByText('社区名')).toBeInTheDocument();
    expect(screen.getByText('7天命中')).toBeInTheDocument();
  });

  it('应该能切换Tab', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    fireEvent.click(screen.getByText('算法验收'));
    // 算法验收Tab显示"算法验收功能（Day 11实现）"
    expect(screen.getByText(/算法验收功能/i)).toBeInTheDocument();
  });

  it('应该显示Mock社区数据', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    expect(screen.getByText('r/startups')).toBeInTheDocument();
    expect(screen.getByText('r/technology')).toBeInTheDocument();
  });

  it('应该显示状态标签', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    // 使用getAllByText因为状态标签和筛选器都有这些文本
    expect(screen.getAllByText('正常').length).toBeGreaterThan(0);
    expect(screen.getAllByText('警告').length).toBeGreaterThan(0);
    expect(screen.getAllByText('异常').length).toBeGreaterThan(0);
  });

  it('应该有搜索功能', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    const searchInput = screen.getByPlaceholderText(/搜索/i) as HTMLInputElement;
    fireEvent.change(searchInput, { target: { value: 'startups' } });
    expect(searchInput.value).toBe('startups');
  });

  it('应该能过滤社区', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    const searchInput = screen.getByPlaceholderText(/搜索/i);
    fireEvent.change(searchInput, { target: { value: 'startups' } });
    expect(screen.getByText('r/startups')).toBeInTheDocument();
    expect(screen.queryByText('r/technology')).not.toBeInTheDocument();
  });

  it('应该有状态筛选器', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    const [statusSelect] = screen.getAllByRole<HTMLSelectElement>('combobox');
    expect(statusSelect).toBeDefined();
    if (!statusSelect) {
      throw new Error('状态筛选器未找到');
    }
  });

  it('应该能按状态筛选', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    const [statusSelect] = screen.getAllByRole<HTMLSelectElement>('combobox');
    if (!statusSelect) {
      throw new Error('状态筛选器未找到');
    }
    fireEvent.change(statusSelect, { target: { value: 'green' } });
    expect(screen.getByText('r/startups')).toBeInTheDocument();
    expect(screen.queryByText('r/technology')).not.toBeInTheDocument();
  });

  it('应该显示功能按钮', () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);
    expect(screen.getByText(/生成.*Patch/i)).toBeInTheDocument();
    expect(screen.getByText(/一键开.*PR/i)).toBeInTheDocument();
  });
});
