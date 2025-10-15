/**
 * 商业机会列表组件
 *
 * 基于 PRD-03 分析引擎设计
 * 展示商业机会信号
 */

import { Lightbulb } from 'lucide-react';
import type { Opportunity } from '@/types';
import { EmptyState } from './EmptyState';

interface OpportunitiesListProps {
  opportunities: Opportunity[];
}

export default function OpportunitiesList({ opportunities }: OpportunitiesListProps) {
  if (!opportunities || opportunities.length === 0) {
    return <EmptyState type="opportunities" />;
  }

  return (
    <div className="space-y-4">
      {opportunities.map((opp, index) => {
        // 如果后端没有提供关键洞察，生成一些基于描述的洞察
        const keyInsights = (opp as any).key_insights || [
          `潜在市场规模：${(opp as any).potential_users || '待评估'}`,
          `相关性评分：${((opp as any).relevance_score * 100 || 0).toFixed(0)}%`,
          '建议优先开发 MVP 验证市场需求',
          '需要进一步的用户调研和竞品分析'
        ];

        return (
          <div key={index} className="rounded-lg border border-border bg-card p-6 transition-shadow hover:shadow-md">
            {/* 标题：灯泡图标 + 文字 */}
            <div className="mb-4 flex items-start gap-3">
              <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
              <h3 className="text-lg font-semibold leading-tight text-foreground">
                {opp.description.split('。')[0] || opp.description}
              </h3>
            </div>

            {/* 描述 */}
            <p className="mb-4 text-sm text-muted-foreground">
              {opp.description}
            </p>

            {/* 关键洞察（紫色圆点） */}
            {keyInsights && keyInsights.length > 0 && (
              <div className="mt-4">
                <h4 className="mb-3 text-sm font-semibold text-foreground">关键洞察：</h4>
                <ul className="space-y-2">
                  {keyInsights.slice(0, 4).map((insight: string, i: number) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

