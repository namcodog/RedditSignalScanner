import React from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, Info, ShieldAlert } from 'lucide-react';
import ProductStatePanel from '@/components/product/ProductStatePanel';

export type SurfaceHeroTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export interface SurfaceHeroBadge {
  label: string;
  tone?: SurfaceHeroTone;
}

export interface SurfaceHeroMetric {
  label: string;
  value: string;
  help?: string;
}

export interface SurfaceHeroProps {
  eyebrow: string;
  title: string;
  description: string;
  badges?: SurfaceHeroBadge[];
  metrics?: SurfaceHeroMetric[];
  nextSteps?: string[];
  warning?: string | null;
  warningTitle?: string | null;
  warningNextStep?: string | null;
}

const BADGE_CLASSNAMES: Record<SurfaceHeroTone, string> = {
  neutral: 'surface-chip',
  info: 'border-blue-200 bg-blue-50/90 text-blue-700',
  success: 'border-emerald-200 bg-emerald-50/90 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50/90 text-amber-700',
  danger: 'border-red-200 bg-red-50/90 text-red-700',
};

const WARNING_ICON: Record<SurfaceHeroTone, React.ReactNode> = {
  neutral: <Info className="w-4 h-4" />,
  info: <Info className="w-4 h-4" />,
  success: <CheckCircle2 className="w-4 h-4" />,
  warning: <AlertTriangle className="w-4 h-4" />,
  danger: <ShieldAlert className="w-4 h-4" />,
};

export const SurfaceHero: React.FC<SurfaceHeroProps> = ({
  eyebrow,
  title,
  description,
  badges = [],
  metrics = [],
  nextSteps = [],
  warning,
  warningTitle,
  warningNextStep,
}) => {
  const primaryStep = nextSteps[0] ?? null;
  const followUpSteps = nextSteps.slice(1).filter(Boolean);

  return (
    <section className="surface-panel relative overflow-hidden rounded-[28px] p-6 md:p-7">
      <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 left-0 h-32 w-32 rounded-full bg-secondary/10 blur-3xl" />
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="relative min-w-0 space-y-4">
          <div className="space-y-2">
            <p className="surface-section-kicker">{eyebrow}</p>
            <div className="surface-rule max-w-40" />
            <h2 className="max-w-4xl text-3xl font-semibold leading-tight text-foreground md:text-[2.3rem]">{title}</h2>
          </div>
          <p className="max-w-3xl text-sm leading-7 text-muted-foreground md:text-[0.96rem]">{description}</p>
        </div>

        {badges.length > 0 && (
          <div className="relative flex flex-wrap gap-2 lg:max-w-sm lg:justify-end">
            {badges.map((badge) => {
              const tone = badge.tone ?? 'neutral';
              return (
                <span
                  key={`${badge.label}-${tone}`}
                  className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${BADGE_CLASSNAMES[tone]}`}
                >
                  <span aria-hidden="true">{WARNING_ICON[tone]}</span>
                  {badge.label}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {warning ? (
        <div className="mt-5">
          <ProductStatePanel
            tone="degraded"
            compact
            title={warningTitle ?? '这次结果不是标准满配版'}
            description={warning}
            nextStep={warningNextStep ?? '先按上面的建议顺着看，再决定要不要继续深挖。'}
          />
        </div>
      ) : null}

      {metrics.length > 0 ? (
        <div className="relative mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="surface-panel-muted rounded-2xl p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{metric.label}</div>
              <div className="surface-number mt-3 text-2xl font-semibold text-foreground">{metric.value}</div>
              {metric.help ? <div className="mt-1 text-xs text-muted-foreground">{metric.help}</div> : null}
            </div>
          ))}
        </div>
      ) : null}

      {primaryStep ? (
        <div className="surface-panel-muted relative mt-6 rounded-2xl p-4 md:p-5">
          <div className="surface-section-kicker">先做这一步</div>
          <div className="mt-2 flex items-start gap-2 text-sm font-semibold text-foreground">
            <ArrowRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" aria-hidden="true" />
            <span>{primaryStep}</span>
          </div>
          {followUpSteps.length > 0 ? (
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              不够再：{followUpSteps.join(' / ')}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
};

export default SurfaceHero;
