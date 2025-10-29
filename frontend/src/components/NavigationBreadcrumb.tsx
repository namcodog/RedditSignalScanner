/**
 * 导航面包屑组件
 * 
 * 基于 最终界面设计效果/components/navigation-breadcrumb.tsx
 * 显示用户当前所在的流程步骤：产品输入 → 信号分析 → 商业洞察
 */

import { ChevronRight, FileText, BarChart3, Lightbulb } from 'lucide-react';

export type NavigationStep = 'input' | 'analysis' | 'report';

export interface NavigationBreadcrumbItem {
  label: string;
  path?: string;
}

interface NavigationBreadcrumbProps {
  currentStep?: NavigationStep;
  onNavigate?: (step: NavigationStep) => void;
  canNavigateBack?: boolean;
  items?: NavigationBreadcrumbItem[];
}

export default function NavigationBreadcrumb({
  currentStep = 'input',
  onNavigate,
  canNavigateBack = false,
  items,
}: NavigationBreadcrumbProps) {
  if (items && items.length > 0) {
    return (
      <nav className="mb-6 flex items-center space-x-2 text-sm text-muted-foreground">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <div key={`${item.label}-${index}`} className="flex items-center space-x-2">
              {index > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground/70" />}
              {isLast ? (
                <span className="font-medium text-foreground">{item.label}</span>
              ) : item.path ? (
                <a
                  href={item.path}
                  className="transition-colors hover:text-foreground"
                >
                  {item.label}
                </a>
              ) : (
                <span>{item.label}</span>
              )}
            </div>
          );
        })}
      </nav>
    );
  }

  const steps = [
    {
      id: 'input' as const,
      title: '产品输入',
      icon: <FileText className="h-4 w-4" />,
      description: '描述您的产品',
    },
    {
      id: 'analysis' as const,
      title: '信号分析',
      icon: <BarChart3 className="h-4 w-4" />,
      description: '处理洞察信息',
    },
    {
      id: 'report' as const,
      title: '商业洞察',
      icon: <Lightbulb className="h-4 w-4" />,
      description: '查看结果',
    },
  ];

  const currentStepIndex = steps.findIndex((step) => step.id === currentStep);

  return (
    <nav className="mb-8 flex items-center justify-center space-x-2 text-sm">
      {steps.map((step, index) => {
        const isActive = step.id === currentStep;
        const isCompleted = index < currentStepIndex;
        const isAccessible = canNavigateBack || index <= currentStepIndex;

        return (
          <div key={step.id} className="flex items-center space-x-2">
            {index > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            <button
              onClick={() => (isAccessible && onNavigate ? onNavigate(step.id) : undefined)}
              className={`flex items-center space-x-2 rounded-md px-3 py-1 transition-colors ${
                isActive
                  ? 'bg-secondary text-secondary-foreground'
                  : isCompleted
                  ? 'text-foreground hover:bg-muted'
                  : isAccessible
                  ? 'text-muted-foreground hover:text-foreground'
                  : 'cursor-default text-muted-foreground/50'
              }`}
            >
              {step.icon}
              <div className="text-left">
                <div className="font-medium">{step.title}</div>
                <div className="text-xs opacity-75">{step.description}</div>
              </div>
            </button>
          </div>
        );
      })}
    </nav>
  );
}
