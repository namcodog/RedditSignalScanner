import { useTranslation } from '@/i18n/TranslationProvider';
import type { EntityMatch, EntitySummary } from '@/types';
import { Tag } from 'lucide-react';

type CategoryKey = keyof EntitySummary;

type EntityHighlightsProps = {
  summary: EntitySummary;
};

const CATEGORY_CONFIG: Array<{
  key: CategoryKey;
  colorClass: string;
  iconColor: string;
}> = [
  {
    key: 'brands',
    colorClass: 'bg-blue-100 text-blue-800 border border-blue-200',
    iconColor: 'text-blue-500',
  },
  {
    key: 'features',
    colorClass: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
    iconColor: 'text-emerald-500',
  },
  {
    key: 'pain_points',
    colorClass: 'bg-rose-100 text-rose-800 border border-rose-200',
    iconColor: 'text-rose-500',
  },
];

export function EntityHighlights({ summary }: EntityHighlightsProps) {
  const { t } = useTranslation();

  const hasMatches =
    summary.brands.length > 0 ||
    summary.features.length > 0 ||
    summary.pain_points.length > 0;

  if (!hasMatches) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        {t('report.entities.empty')}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {CATEGORY_CONFIG.map(({ key, colorClass, iconColor }) => {
        const items: EntityMatch[] = summary[key] ?? [];
        if (items.length === 0) {
          return null;
        }

        return (
          <div key={key} className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Tag className={`h-4 w-4 ${iconColor}`} />
              <span>{t(`report.entities.categories.${key}`)}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {items.map((item) => (
                <span
                  key={item.name}
                  className={`inline-flex items-center rounded-full px-3 py-1 text-sm ${colorClass}`}
                >
                  <span className="font-medium">{item.name}</span>
                  <span className="ml-2 text-xs text-current/70">
                    {t('report.entities.mentions', { count: item.mentions })}
                  </span>
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
