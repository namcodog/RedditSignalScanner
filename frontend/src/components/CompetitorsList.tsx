/**
 * 竞品列表组件
 *
 * 基于 PRD-03 分析引擎设计
 * 展示竞品分析信号
 */

import type { Competitor } from '@/types';
import { EmptyState } from './EmptyState';
import { ThumbsUp } from 'lucide-react';

interface CompetitorsListProps {
  competitors: Competitor[];
}

export default function CompetitorsList({ competitors }: CompetitorsListProps) {
  if (!competitors || competitors.length === 0) {
    return <EmptyState type="competitors" />;
  }

  // 如果后端没有提供市场份额，计算它
  const totalMentions = competitors.reduce((sum, c) => sum + c.mentions, 0);
  const competitorsWithShare = competitors.map(c => ({
    ...c,
    market_share: (c as any).market_share !== undefined
      ? (c as any).market_share
      : Math.round((c.mentions / totalMentions) * 100)
  }));

  return (
    <div className="space-y-4">
      {competitorsWithShare.map((competitor, index) => (
        <div key={index} className="rounded-lg border border-border bg-card p-6 transition-shadow hover:shadow-md">
          {/* 头部：图标 + 名称，右侧：点赞 + 提及次数 + 市场份额 */}
          <div className="mb-6 flex items-start justify-between gap-4">
            {/* 左侧：圆形图标 + 名称 */}
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-secondary bg-secondary/10">
                <span className="text-lg font-bold text-secondary">
                  {competitor.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <h3 className="text-xl font-bold text-foreground">{competitor.name}</h3>
            </div>

            {/* 右侧：点赞图标 + 提及次数 + 紫色底色市场份额 */}
            <div className="flex shrink-0 items-center gap-3">
              <ThumbsUp className="h-4 w-4 text-green-600" />
              <span className="text-sm text-muted-foreground">
                {competitor.mentions} 条帖子提及
              </span>
              {competitor.market_share !== undefined && (
                <span className="inline-flex items-center rounded-md bg-secondary px-2.5 py-0.5 text-sm font-semibold text-white">
                  {competitor.market_share}% 市场份额
                </span>
              )}
            </div>
          </div>

          {/* 优势和劣势：两列布局 */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* 优势（左列，绿色） */}
            {competitor.strengths && competitor.strengths.length > 0 && (
              <div>
                <h4 className="mb-3 text-sm font-semibold text-green-700">优势</h4>
                <ul className="space-y-2">
                  {competitor.strengths.map((strength, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-green-600" />
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 劣势（右列，红色） */}
            {competitor.weaknesses && competitor.weaknesses.length > 0 && (
              <div>
                <h4 className="mb-3 text-sm font-semibold text-red-700">劣势</h4>
                <ul className="space-y-2">
                  {competitor.weaknesses.map((weakness, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-600" />
                      <span>{weakness}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

