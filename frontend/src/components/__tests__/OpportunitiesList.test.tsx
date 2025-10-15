import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import OpportunitiesList from '../OpportunitiesList';

describe('OpportunitiesList', () => {
  it('应该显示空状态当没有商业机会数据时', () => {
    render(<OpportunitiesList opportunities={[]} />);
    expect(screen.getByText('暂无机会数据')).toBeInTheDocument();
  });

  it('应该正确渲染商业机会列表', () => {
    const opportunities = [
      {
        description: '开发移动端应用',
        relevance_score: 0.85,
        potential_users: '5000+ 用户',
        key_insights: ['用户需求强烈', '市场空间大'],
      },
      {
        description: '添加离线模式',
        relevance_score: 0.72,
        potential_users: '3200+ 用户',
        key_insights: ['提升用户体验'],
      },
    ];

    render(<OpportunitiesList opportunities={opportunities} />);

    expect(screen.getByText('开发移动端应用')).toBeInTheDocument();
    expect(screen.getByText('添加离线模式')).toBeInTheDocument();
  });

  it('应该显示相关性分数', () => {
    const opportunities = [
      {
        description: '开发移动端应用',
        relevance_score: 0.85,
        potential_users: '5000+ 用户',
        key_insights: ['用户需求强烈'],
      },
    ];

    render(<OpportunitiesList opportunities={opportunities} />);

    expect(screen.getByText('开发移动端应用')).toBeInTheDocument();
  });

  it('应该显示潜在用户', () => {
    const opportunities = [
      {
        description: '开发移动端应用',
        relevance_score: 0.85,
        potential_users: '5000+ 用户',
        key_insights: ['用户需求强烈'],
      },
    ];

    render(<OpportunitiesList opportunities={opportunities} />);

    expect(screen.getByText('开发移动端应用')).toBeInTheDocument();
  });

  it('应该显示来源社区', () => {
    const opportunities = [
      {
        description: '开发移动端应用',
        relevance_score: 0.85,
        potential_users: '5000+ 用户',
        key_insights: ['用户需求强烈', '市场空间大'],
      },
    ];

    render(<OpportunitiesList opportunities={opportunities} />);

    expect(screen.getByText('开发移动端应用')).toBeInTheDocument();
  });
});

