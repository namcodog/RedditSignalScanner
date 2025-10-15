import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PainPointsList from '../PainPointsList';

describe('PainPointsList', () => {
  it('应该显示空状态当没有痛点数据时', () => {
    render(<PainPointsList painPoints={[]} />);
    expect(screen.getByText('暂无痛点数据')).toBeInTheDocument();
  });

  it('应该正确渲染痛点列表', () => {
    const painPoints = [
      {
        description: '产品价格太高',
        frequency: 42,
        sentiment_score: -0.6,
        severity: 'high' as const,
        example_posts: [
          { community: 'r/productivity', content: '价格太贵', upvotes: 100 },
        ],
        user_examples: ['价格太贵了', '不值这个价'],
      },
      {
        description: '缺少移动端支持',
        frequency: 28,
        sentiment_score: -0.4,
        severity: 'medium' as const,
        example_posts: [
          { community: 'r/apps', content: '没有手机版', upvotes: 80 },
        ],
        user_examples: ['需要手机版'],
      },
    ];

    render(<PainPointsList painPoints={painPoints} />);

    expect(screen.getByText('产品价格太高')).toBeInTheDocument();
    expect(screen.getByText('缺少移动端支持')).toBeInTheDocument();
    expect(screen.getByText('42 条帖子提及')).toBeInTheDocument();
    expect(screen.getByText('28 条帖子提及')).toBeInTheDocument();
  });

  it('应该显示社区标签', () => {
    const painPoints = [
      {
        description: '产品价格太高',
        frequency: 42,
        sentiment_score: -0.6,
        severity: 'high' as const,
        user_examples: ['价格太贵'],
        example_posts: [
          { community: 'r/productivity', content: '价格太贵', upvotes: 100 },
          { community: 'r/apps', content: '太贵了', upvotes: 50 },
        ],
      },
    ];

    render(<PainPointsList painPoints={painPoints} />);

    expect(screen.getByText('r/productivity')).toBeInTheDocument();
    expect(screen.getByText('r/apps')).toBeInTheDocument();
  });

  it('应该显示提及次数', () => {
    const painPoints = [
      {
        description: '产品价格太高',
        frequency: 42,
        sentiment_score: -0.6,
        severity: 'high' as const,
        user_examples: [],
        example_posts: [],
      },
    ];

    render(<PainPointsList painPoints={painPoints} />);

    expect(screen.getByText('42 条帖子提及')).toBeInTheDocument();
  });
});

