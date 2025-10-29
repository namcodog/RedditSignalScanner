/**
 * InsightCard Component
 * 
 * 洞察卡片组件：展示单个洞察卡片的标题、摘要、置信度、时间窗口、相关子版块
 * 支持点击展开/收起证据列表
 * 
 * 最后更新: 2025-10-22
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, Lightbulb, Calendar, TrendingUp } from 'lucide-react';
import type { InsightCard as InsightCardType } from '@/types';

interface InsightCardProps {
  /** 洞察卡片数据 */
  insight: InsightCardType;
  
  /** 是否默认展开证据 */
  defaultExpanded?: boolean;
  
  /** 证据展开/收起回调 */
  onToggleEvidence?: (insightId: string, expanded: boolean) => void;
}

/**
 * 洞察卡片组件
 */
export default function InsightCard({
  insight,
  defaultExpanded = false,
  onToggleEvidence,
}: InsightCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onToggleEvidence?.(insight.id, newExpanded);
  };

  // 置信度样式映射
  const getConfidenceStyle = (confidence: number) => {
    if (confidence >= 0.8) {
      return 'bg-green-100 text-green-800';
    } else if (confidence >= 0.6) {
      return 'bg-yellow-100 text-yellow-800';
    } else {
      return 'bg-orange-100 text-orange-800';
    }
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) {
      return '高';
    } else if (confidence >= 0.6) {
      return '中';
    } else {
      return '低';
    }
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6 transition-shadow hover:shadow-md">
      {/* 顶部：图标 + 标题，右侧：置信度 + 证据数量 */}
      <div className="mb-4 flex items-start justify-between gap-4">
        {/* 左侧：图标 + 标题 */}
        <div className="flex items-start gap-3 flex-1">
          <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
          <h3 className="text-lg font-semibold leading-tight text-foreground">
            {insight.title}
          </h3>
        </div>

        {/* 右侧：置信度标签 + 证据数量 */}
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-semibold ${getConfidenceStyle(
              insight.confidence
            )}`}
          >
            置信度: {getConfidenceLabel(insight.confidence)}
          </span>
          <span className="text-sm text-muted-foreground">
            {insight.evidence.length} 条证据
          </span>
        </div>
      </div>

      {/* 摘要 */}
      <p className="mb-4 text-sm text-muted-foreground">{insight.summary}</p>

      {/* 元数据：时间窗口 + 相关子版块 */}
      <div className="mb-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
        {/* 时间窗口 */}
        <div className="flex items-center gap-1.5">
          <Calendar className="h-4 w-4" />
          <span>{insight.time_window}</span>
        </div>

        {/* 相关子版块 */}
        {insight.subreddits.length > 0 && (
          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-4 w-4" />
            <span>
              {insight.subreddits.slice(0, 3).join(', ')}
              {insight.subreddits.length > 3 && ` +${insight.subreddits.length - 3}`}
            </span>
          </div>
        )}
      </div>

      {/* 展开/收起证据按钮 */}
      {insight.evidence.length > 0 && (
        <button
          onClick={handleToggle}
          className="flex w-full items-center justify-center gap-2 rounded-md border border-border bg-muted/30 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/50"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-4 w-4" />
              <span>收起证据</span>
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" />
              <span>查看证据 ({insight.evidence.length})</span>
            </>
          )}
        </button>
      )}

      {/* 证据列表（展开时显示） */}
      {isExpanded && insight.evidence.length > 0 && (
        <div className="mt-4 space-y-3">
          {insight.evidence.map((evidence) => (
            <div
              key={evidence.id}
              className="border-l-4 border-secondary bg-muted/30 pl-4 py-3"
            >
              {/* 证据元数据 */}
              <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium">{evidence.subreddit}</span>
                <span>
                  {new Date(evidence.timestamp).toLocaleDateString('zh-CN', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              </div>

              {/* 证据摘录 */}
              <p className="text-sm italic text-muted-foreground mb-2">
                "{evidence.excerpt}"
              </p>

              {/* 证据链接 + 分数 */}
              <div className="flex items-center justify-between">
                <a
                  href={evidence.post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline"
                >
                  查看原帖 →
                </a>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">相关性:</span>
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-16 rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-secondary transition-all"
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(0, (evidence.score ?? 0) * 100)
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium text-foreground">
                      {evidence.score != null
                        ? `${(evidence.score * 100).toFixed(0)}%`
                        : '待定'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
