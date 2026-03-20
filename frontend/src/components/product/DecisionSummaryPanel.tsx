import React from 'react';
import { ArrowRight, CheckCircle2, Compass, Sparkles } from 'lucide-react';

type DecisionActionTone = 'primary' | 'secondary';

export interface DecisionSummaryReason {
  title: string;
  description: string;
}

export interface DecisionSummarySignal {
  label: string;
  value: string;
  help?: string;
}

export interface DecisionSummaryAction {
  label: string;
  onClick: () => void;
  tone?: DecisionActionTone;
}

export interface DecisionSummaryPanelProps {
  title: string;
  verdictTitle: string;
  verdictDescription: string;
  reasonsTitle?: string;
  reasons: DecisionSummaryReason[];
  signals?: DecisionSummarySignal[];
  nextStepTitle?: string;
  nextStepDescription: string;
  actions?: DecisionSummaryAction[];
}

const ACTION_CLASSNAMES: Record<DecisionActionTone, string> = {
  primary: 'surface-action-primary',
  secondary: 'surface-action-secondary',
};

const DecisionSummaryPanel: React.FC<DecisionSummaryPanelProps> = ({
  title,
  verdictTitle,
  verdictDescription,
  reasonsTitle = '为什么值得继续看',
  reasons,
  signals = [],
  nextStepTitle = '下一步动作',
  nextStepDescription,
  actions = [],
}) => {
  return (
    <section className="surface-panel rounded-[28px] p-6 md:p-7">
      <div className="surface-section-kicker">
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        <span>{title}</span>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[1.08fr,1fr,1fr]">
        <article className="surface-panel-strong rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-primary-foreground/80">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            <span>现在建议</span>
          </div>
          <h3 className="mt-3 text-2xl font-semibold text-primary-foreground">{verdictTitle}</h3>
          <p className="mt-3 text-sm leading-7 text-primary-foreground/76">{verdictDescription}</p>
        </article>

        <article className="surface-panel-muted rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            <Compass className="h-4 w-4 text-primary" aria-hidden="true" />
            <span>{reasonsTitle}</span>
          </div>
          <div className="mt-4 space-y-3">
            {reasons.map((reason) => (
              <div key={`${reason.title}-${reason.description}`} className="rounded-2xl border border-border/90 bg-card/80 p-3.5">
                <div className="text-sm font-semibold text-foreground">{reason.title}</div>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{reason.description}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="surface-panel-muted rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
            <ArrowRight className="h-4 w-4 text-primary" aria-hidden="true" />
            <span>{nextStepTitle}</span>
          </div>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">{nextStepDescription}</p>
          {actions.length > 0 ? (
            <div className="mt-4 flex flex-col gap-3">
              {actions.map((action) => {
                const tone = action.tone ?? 'secondary';
                return (
                  <button
                    key={action.label}
                    type="button"
                    onClick={action.onClick}
                    className={`inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${ACTION_CLASSNAMES[tone]}`}
                  >
                    {action.label}
                  </button>
                );
              })}
            </div>
          ) : null}
        </article>
      </div>

      {signals.length > 0 ? (
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {signals.map((signal) => (
            <div key={`${signal.label}-${signal.value}`} className="surface-panel-muted rounded-2xl p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{signal.label}</div>
              <div className="surface-number mt-2 text-lg font-semibold text-foreground">{signal.value}</div>
              {signal.help ? <div className="mt-1 text-xs text-muted-foreground">{signal.help}</div> : null}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
};

export default DecisionSummaryPanel;
