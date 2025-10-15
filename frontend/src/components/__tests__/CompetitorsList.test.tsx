import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompetitorsList from '../CompetitorsList';
import { Sentiment } from '@/types';

describe('CompetitorsList', () => {
  it('应该显示空状态当没有竞品数据时', () => {
    render(<CompetitorsList competitors={[]} />);
    expect(screen.getByText('暂无竞品数据')).toBeInTheDocument();
  });

  it('应该正确渲染竞品列表', () => {
    const competitors = [
      {
        name: 'Notion',
        mentions: 156,
        sentiment: Sentiment.POSITIVE,
        strengths: ['协作', '模板', '数据库'],
        weaknesses: ['价格高'],
      },
      {
        name: 'Trello',
        mentions: 89,
        sentiment: Sentiment.POSITIVE,
        strengths: ['看板', '简单', '免费'],
        weaknesses: ['功能少'],
      },
    ];

    render(<CompetitorsList competitors={competitors} />);

    expect(screen.getByText('竞品分析')).toBeInTheDocument();
    expect(screen.getByText('发现 2 个竞争对手')).toBeInTheDocument();
    expect(screen.getByText('Notion')).toBeInTheDocument();
    expect(screen.getByText('Trello')).toBeInTheDocument();
    expect(screen.getByText('156 次提及')).toBeInTheDocument();
    expect(screen.getByText('89 次提及')).toBeInTheDocument();
  });

  it('应该显示优势标签', () => {
    const competitors = [
      {
        name: 'Notion',
        mentions: 156,
        sentiment: Sentiment.POSITIVE,
        strengths: ['协作', '模板'],
        weaknesses: [],
      },
    ];

    render(<CompetitorsList competitors={competitors} />);

    expect(screen.getByText('协作')).toBeInTheDocument();
    expect(screen.getByText('模板')).toBeInTheDocument();
  });

  it('应该显示情感倾向', () => {
    const competitors = [
      {
        name: 'Notion',
        mentions: 156,
        sentiment: Sentiment.POSITIVE,
        strengths: [],
        weaknesses: [],
      },
    ];

    render(<CompetitorsList competitors={competitors} />);

    expect(screen.getByText(/正面/)).toBeInTheDocument();
  });
});

