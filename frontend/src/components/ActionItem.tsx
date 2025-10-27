import { ExternalLink, Lightbulb, Star } from 'lucide-react';
import type { ActionItem } from '@/types';
import { EmptyState } from './EmptyState';
import { useTranslation } from '@/i18n/TranslationProvider';

type ActionItemProps = {
  item: ActionItem;
};

type PriorityStarsProps = {
  score: number;
};

function PriorityStars({ score }: PriorityStarsProps) {
  const stars = Math.round(Math.max(0, Math.min(1, score)) * 5);
  const items = Array.from({ length: 5 }, (_, index) => index < stars);

  return (
    <div className="flex items-center gap-1 text-sm">
      {items.map((filled, index) => (
        <Star
          key={index}
          className={`h-4 w-4 ${filled ? 'fill-yellow-400 text-yellow-400' : 'text-border'}`}
        />
      ))}
      <span className="text-xs text-muted-foreground">{Math.round(score * 100)}%</span>
    </div>
  );
}

export function ActionItemCard({ item }: ActionItemProps) {
  return (
    <div className="rounded-lg border border-border bg-card/70 p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-4 flex items-start gap-3">
        <div className="rounded-md bg-secondary/20 p-2 text-secondary">
          <Lightbulb className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-foreground">{item.problem_definition}</h3>
            <PriorityStars score={item.priority} />
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span>信心 {Math.round(item.confidence * 100)}%</span>
            <span>紧迫度 {Math.round(item.urgency * 100)}%</span>
            <span>产品契合度 {Math.round(item.product_fit * 100)}%</span>
          </div>
        </div>
      </div>

      {item.evidence_chain.length > 0 && (
        <div className="mb-4 space-y-2">
          <h4 className="text-sm font-semibold text-foreground">证据链</h4>
          <ul className="space-y-2">
            {item.evidence_chain.map((evidence, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                <div>
                  <div className="flex items-center gap-2">
                    <span>{evidence.title}</span>
                    {evidence.url && (
                      <a
                        href={evidence.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-secondary hover:underline"
                      >
                        查看原帖 <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{evidence.note}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {item.suggested_actions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-foreground">建议行动</h4>
          <ul className="space-y-2">
            {item.suggested_actions.map((action, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export interface ActionItemsListProps {
  items: ActionItem[];
}

export function ActionItemsList({ items }: ActionItemsListProps) {
  const { t } = useTranslation();

  if (!items || items.length === 0) {
    return (
      <EmptyState
        type="general"
        title={t('report.actions.empty')}
        description={t('report.actions.startNew')}
        className="py-10"
      />
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <ActionItemCard key={index} item={item} />
      ))}
    </div>
  );
}
