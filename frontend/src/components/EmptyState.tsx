/**
 * 空状态组件
 * 
 * Day 9 UI优化任务
 * 用于展示各种空状态场景，提供更好的用户体验
 */

import React from 'react';
import { AlertCircle, MessageSquare, Lightbulb, Search } from 'lucide-react';

interface EmptyStateProps {
  type: 'pain-points' | 'competitors' | 'opportunities' | 'general';
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  className?: string;
}

/**
 * 空状态组件
 * 
 * 根据不同类型展示不同的图标和文案
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  type,
  title,
  description,
  icon,
  className = '',
}) => {
  // 默认配置
  const configs = {
    'pain-points': {
      icon: <AlertCircle className="h-16 w-16 text-muted-foreground/50" />,
      title: '暂无痛点数据',
      description: '分析结果中未发现明显的用户痛点信号。这可能意味着该领域的用户满意度较高，或需要调整搜索关键词。',
      bgColor: 'bg-red-50 dark:bg-red-950/10',
      borderColor: 'border-red-200 dark:border-red-900/20',
    },
    competitors: {
      icon: <MessageSquare className="h-16 w-16 text-muted-foreground/50" />,
      title: '暂无竞品数据',
      description: '分析结果中未发现相关竞品提及。这可能是一个蓝海市场机会，或需要扩大搜索范围。',
      bgColor: 'bg-secondary/10',
      borderColor: 'border-secondary/20',
    },
    opportunities: {
      icon: <Lightbulb className="h-16 w-16 text-muted-foreground/50" />,
      title: '暂无机会数据',
      description: '分析结果中未发现明显的商业机会信号。建议查看痛点和竞品分析，寻找潜在切入点。',
      bgColor: 'bg-green-50 dark:bg-green-950/10',
      borderColor: 'border-green-200 dark:border-green-900/20',
    },
    general: {
      icon: <Search className="h-16 w-16 text-muted-foreground/50" />,
      title: '暂无数据',
      description: '当前没有可显示的数据。',
      bgColor: 'bg-muted/10',
      borderColor: 'border-border',
    },
  };

  const config = configs[type];
  const displayIcon = icon || config.icon;
  const displayTitle = title || config.title;
  const displayDescription = description || config.description;

  return (
    <div
      className={`rounded-xl border border-dashed ${config.borderColor} ${config.bgColor} p-12 text-center ${className}`}
    >
      <div className="mx-auto mb-4 flex items-center justify-center">
        {displayIcon}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-foreground">
        {displayTitle}
      </h3>
      <p className="mx-auto max-w-md text-sm text-muted-foreground">
        {displayDescription}
      </p>
    </div>
  );
};

/**
 * 紧凑型空状态组件
 * 用于列表中的空状态
 */
export const CompactEmptyState: React.FC<{
  message: string;
  icon?: React.ReactNode;
}> = ({ message, icon }) => {
  return (
    <div className="flex items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-muted/10 p-6">
      {icon && <div className="text-muted-foreground/50">{icon}</div>}
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
};

export default EmptyState;

