import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, FileWarning, SearchX } from 'lucide-react';

type ProductStateTone = 'empty' | 'degraded' | 'error';
type ProductStateActionTone = 'primary' | 'secondary';

export interface ProductStateAction {
  label: string;
  onClick?: () => void;
  to?: string;
  tone?: ProductStateActionTone;
}

export interface ProductStatePanelProps {
  tone: ProductStateTone;
  title: string;
  description: string;
  nextStep?: string | null;
  actions?: ProductStateAction[];
  compact?: boolean;
  className?: string;
}

const TONE_CONFIG: Record<
  ProductStateTone,
  {
    icon: React.ReactNode;
    border: string;
    background: string;
    title: string;
    description: string;
  }
> = {
  empty: {
    icon: <SearchX className="h-5 w-5" />,
    border: 'border-stone-200',
    background: 'bg-stone-50/90',
    title: 'text-slate-900',
    description: 'text-slate-600',
  },
  degraded: {
    icon: <AlertTriangle className="h-5 w-5" />,
    border: 'border-amber-200',
    background: 'bg-amber-50/90',
    title: 'text-amber-900',
    description: 'text-amber-800',
  },
  error: {
    icon: <FileWarning className="h-5 w-5" />,
    border: 'border-red-200',
    background: 'bg-red-50/90',
    title: 'text-red-900',
    description: 'text-red-800',
  },
};

const ACTION_CLASSNAMES: Record<ProductStateActionTone, string> = {
  primary: 'surface-action-primary',
  secondary: 'surface-action-secondary',
};

export const ProductStatePanel: React.FC<ProductStatePanelProps> = ({
  tone,
  title,
  description,
  nextStep,
  actions = [],
  compact = false,
  className = '',
}) => {
  const config = TONE_CONFIG[tone];

  return (
    <section
      data-testid="product-state-panel"
      className={`rounded-[24px] border ${config.border} ${config.background} ${
        compact ? 'p-4' : 'p-6'
      } ${className}`}
    >
      <div className={`flex ${compact ? 'gap-3' : 'gap-4'}`}>
        <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-background/90 text-current shadow-sm">
          {config.icon}
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <h3 className={`font-semibold ${compact ? 'text-base' : 'text-lg'} ${config.title}`}>
            {title}
          </h3>
          <p className={`leading-6 ${compact ? 'text-sm' : 'text-sm'} ${config.description}`}>
            {description}
          </p>
          {nextStep ? (
            <div className={`flex items-start gap-2 ${compact ? 'text-sm' : 'text-sm'} ${config.description}`}>
              <ArrowRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" aria-hidden="true" />
              <span>
                <span className="font-medium">下一步：</span>
                {nextStep}
              </span>
            </div>
          ) : null}
          {actions.length > 0 ? (
            <div className="flex flex-wrap gap-3 pt-1">
              {actions.map((action) => {
                const toneKey = action.tone ?? 'secondary';
                const className = `inline-flex h-10 items-center justify-center rounded-xl border px-4 text-sm font-medium transition-colors ${ACTION_CLASSNAMES[toneKey]}`;

                if (action.to) {
                  return (
                    <Link key={`${action.label}-${action.to}`} to={action.to} className={className}>
                      {action.label}
                    </Link>
                  );
                }

                return (
                  <button
                    key={action.label}
                    type="button"
                    onClick={action.onClick}
                    className={className}
                  >
                    {action.label}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
};

export default ProductStatePanel;
