/**
 * 痛点列表组件
 *
 * 基于 PRD-03 分析引擎设计
 * 展示用户痛点信号
 */

import type { PainPointViewModel } from '@/types';
import { EmptyState } from './EmptyState';
import { AlertTriangle } from 'lucide-react';

interface PainPointsListProps {
  painPoints: PainPointViewModel[];
}

export default function PainPointsList({ painPoints }: PainPointsListProps) {
  if (!painPoints || painPoints.length === 0) {
    return <EmptyState type="pain-points" />;
  }

  // 严重程度样式映射
  const getSeverityStyle = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
    }
  };

  const getSeverityLabel = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return '高';
      case 'medium':
        return '中';
      case 'low':
        return '低';
    }
  };

  return (
    <div className="space-y-4">
      {painPoints.map((pain, index) => {
        return (
          <div key={index} className="rounded-lg border border-border bg-card p-6 transition-shadow hover:shadow-md">
            {/* 顶部：图标 + 标题，右侧：严重程度 + 提及次数 */}
            <div className="mb-4 flex items-start justify-between gap-4">
              {/* 左侧：图标 + 标题 */}
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                <h3 className="text-lg font-semibold leading-tight text-foreground">
                  {pain.description.split('。')[0]}
                </h3>
              </div>

              {/* 右侧：严重程度标签 + 提及次数 */}
              <div className="flex shrink-0 items-center gap-2">
                <span className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-semibold ${getSeverityStyle(pain.severity)}`}>
                  {getSeverityLabel(pain.severity)}
                </span>
                <span className="text-sm text-muted-foreground">
                  {pain.frequency} 条帖子提及
                </span>
              </div>
            </div>

            {/* 内容描述 */}
            <p className="mb-4 text-sm text-muted-foreground">
              {pain.description}
            </p>

            {/* 用户示例（紫色左边框） */}
            {pain.userExamples.length > 0 && (
              <div>
                <h4 className="mb-3 text-sm font-semibold text-foreground">用户示例：</h4>
                <div className="space-y-3">
                  {pain.userExamples.slice(0, 3).map((example, i) => (
                    <div key={i} className="border-l-4 border-secondary bg-muted/30 pl-4 py-2">
                      <p className="text-sm italic text-muted-foreground">
                        "{example.trim()}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
