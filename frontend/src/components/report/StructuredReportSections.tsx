import clsx from 'clsx';
import { Info } from 'lucide-react';

import { normalizeLine } from '@/lib/report-markdown';
import { normalizeRedditUrl } from '@/lib/reddit-url';
import type { StructuredReport } from '@/types/report/response';

const TERM_EXPLANATIONS = {
  battlefields: {
    label: '战场',
    help: '战场指最值得先进入的核心社区。这里不是泛泛列社区，而是告诉你先去哪一层人群里验证问题和机会。',
  },
  drivers: {
    label: '驱动力',
    help: '驱动力不是功能清单，而是用户为什么愿意掏钱、为什么会下决心的真实原因。',
  },
  opportunities: {
    label: '机会',
    help: '机会不是空泛方向，而是已经连上痛点、社群和卖点的可执行产品切口。',
  },
} as const;

const SECTION_SUMMARIES = {
  1: '市场切片：快速抓住这条赛道的核心矛盾、主要人群和切入价值。',
  2: '决策信号：从热度演变、供需缺口到核心社群，快速判断这题值不值得做。',
  3: '市场诊断：把竞争密度、用户抱怨和进场窗口放在一条线上看清。',
  4: '战场排序：优先进入最容易看见真实抱怨、也最容易验证方案的社区。',
  5: '痛点拆解：把高频抱怨翻译成具体损失，判断值不值得做成产品。',
  6: '购买动因：用户最后愿不愿意掏钱，往往取决于他们最在意的结果。',
  7: '机会收口：把痛点、社群和卖点连起来，留下能直接拿去做的产品切口。',
} as const;

type PainEvidenceSource = {
  example_posts?: Array<{
    community?: string | undefined;
    content?: string | null | undefined;
    url?: string | null | undefined;
    permalink?: string | null | undefined;
  }>;
};

type CanonicalEvidenceItem = {
  title: string;
  url?: string | null | undefined;
  note: string;
};

type CanonicalCard = StructuredReport['decision_cards'][number];

type DecisionCardView = CanonicalCard & {
  displayTitle: string;
};

type StructuredReportSectionsProps = {
  structured: StructuredReport;
  overviewLead: string;
  overviewDetails: string[];
  painEvidenceSources?: PainEvidenceSource[];
  sectionTitles?: Partial<
    Record<1 | 2 | 3 | 4 | 5 | 6 | 7, string | undefined>
  >;
  className?: string;
};

const DECISION_CARD_ORDER: Array<{ displayTitle: string; keywords: string[] }> =
  [
    { displayTitle: '需求趋势', keywords: ['趋势'] },
    {
      displayTitle: '难题与攻略比',
      keywords: ['P/S', '比例', '问题/解决方案', '难题'],
    },
    { displayTitle: '核心社群', keywords: ['社群', '核心战场'] },
    { displayTitle: '落地机会', keywords: ['机会'] },
  ];

const orderDecisionCards = (cards: CanonicalCard[]): DecisionCardView[] => {
  const used = new Set<number>();

  return DECISION_CARD_ORDER.map((rule, position) => {
    const matchedIndex = cards.findIndex(
      (card, index) =>
        !used.has(index) &&
        rule.keywords.some((keyword) =>
          `${card.title} ${card.conclusion}`.includes(keyword)
        )
    );
    const fallbackIndex =
      matchedIndex >= 0
        ? matchedIndex
        : cards.findIndex((_, index) => !used.has(index));
    if (fallbackIndex < 0) return null;
    const card = cards[fallbackIndex];
    if (!card) return null;
    used.add(fallbackIndex);
    return {
      ...card,
      displayTitle: rule.displayTitle || card.title || `判断 ${position + 1}`,
    };
  }).filter(Boolean) as DecisionCardView[];
};

const TooltipBadge = ({ label, help }: { label: string; help: string }) => (
  <div className="group relative inline-flex items-center">
    <button
      type="button"
      className="surface-help-trigger"
      aria-label={`解释：什么是${label}`}
    >
      <Info aria-hidden="true" className="h-3.5 w-3.5" />
    </button>
    <div className="surface-help-popover" role="tooltip">
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/72">
        术语解释
      </div>
      <div className="mt-2 text-sm font-semibold text-foreground">
        什么是{label}
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{help}</p>
    </div>
  </div>
);

const SectionHeading = ({
  order,
  title,
  summary,
  termKey,
}: {
  order: number;
  title: string;
  summary?: string;
  termKey?: keyof typeof TERM_EXPLANATIONS;
}) => (
  <div className="space-y-3">
    <div className="flex flex-wrap items-center gap-3">
      <span className="editorial-order-badge">
        {String(order).padStart(2, '0')}
      </span>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <h2 className="font-display text-2xl font-semibold leading-tight text-foreground md:text-[2rem]">
          {order}. {title}
        </h2>
        {termKey ? (
          <TooltipBadge
            label={TERM_EXPLANATIONS[termKey].label}
            help={TERM_EXPLANATIONS[termKey].help}
          />
        ) : null}
      </div>
    </div>
    {summary ? (
      <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
        {summary}
      </p>
    ) : null}
  </div>
);

const buildPainEvidenceLinks = (
  structuredEvidence: CanonicalEvidenceItem[] | undefined,
  sources: PainEvidenceSource[] | undefined,
  index: number
) => {
  if (structuredEvidence && structuredEvidence.length > 0) {
    return structuredEvidence
      .reduce<Array<{ href: string; label: string; text: string }>>(
        (items, evidence) => {
          const href = normalizeRedditUrl(evidence.url);
          const text = (evidence.title || '').trim();
          if (!href || !text) return items;
          items.push({
            href,
            label: evidence.note || 'Reddit · 去 Reddit 看原帖',
            text: text.length > 96 ? `${text.slice(0, 96)}…` : text,
          });
          return items;
        },
        []
      )
      .slice(0, 2);
  }

  return (sources?.[index]?.example_posts ?? [])
    .reduce<Array<{ href: string; label: string; text: string }>>(
      (items, post) => {
        const href = normalizeRedditUrl(post.url, post.permalink);
        const text = (post.content || '').trim();
        if (!href || !text) return items;
        items.push({
          href,
          label: `${post.community || 'Reddit'} · 去 Reddit 看原帖`,
          text: text.length > 96 ? `${text.slice(0, 96)}…` : text,
        });
        return items;
      },
      []
    )
    .slice(0, 2);
};

const StructuredReportSections = ({
  structured,
  overviewLead,
  overviewDetails,
  painEvidenceSources,
  sectionTitles,
  className,
}: StructuredReportSectionsProps) => {
  const orderedDecisionCards = orderDecisionCards(
    structured.decision_cards ?? []
  );

  return (
    <div className={clsx('space-y-5', className)}>
      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={1}
          title={sectionTitles?.[1] ?? '开篇概览'}
          summary={SECTION_SUMMARIES[1]}
        />
        <article className="editorial-card-primary mt-5 rounded-[28px] p-6 md:p-7">
          <p className="max-w-4xl break-words text-[1.55rem] font-semibold leading-[1.4] text-primary-foreground md:text-[1.9rem]">
            {overviewLead}
          </p>
          <div className="mt-5 space-y-3 text-[0.98rem] leading-8 text-primary-foreground/78">
            {overviewDetails.map((detail) => (
              <p key={detail} className="max-w-4xl break-words">
                {normalizeLine(detail)}
              </p>
            ))}
          </div>
        </article>
      </section>

      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={2}
          title={sectionTitles?.[2] ?? '决策风向标'}
          summary={SECTION_SUMMARIES[2]}
        />
        <div className="mt-5 space-y-4">
          {orderedDecisionCards.map((card, index) => (
            <article
              key={`${card.displayTitle}-${index}`}
              className={clsx(
                'rounded-[26px] p-5 md:p-6',
                index === 0
                  ? 'editorial-card-primary'
                  : 'editorial-card-secondary'
              )}
            >
              <div
                className={clsx(
                  'text-[11px] font-semibold uppercase tracking-[0.18em]',
                  index === 0 ? 'text-primary-foreground/72' : 'text-primary'
                )}
              >
                {card.displayTitle}
              </div>
              <p
                className={clsx(
                  'mt-3 break-words font-semibold leading-[1.35]',
                  index === 0
                    ? 'text-primary-foreground text-[1.55rem] md:text-[1.9rem]'
                    : 'text-foreground text-[1.18rem] md:text-[1.28rem]'
                )}
              >
                {card.conclusion}
              </p>
              {card.details.length > 0 ? (
                <div
                  className={clsx(
                    'mt-4 space-y-2 text-[0.98rem] leading-8',
                    index === 0
                      ? 'text-primary-foreground/78'
                      : 'text-muted-foreground'
                  )}
                >
                  {card.details.map((detail) => (
                    <p key={detail} className="break-words">
                      {normalizeLine(detail)}
                    </p>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={3}
          title={sectionTitles?.[3] ?? '概览（市场健康度诊断）'}
          summary={SECTION_SUMMARIES[3]}
        />
        <div className="mt-5 grid gap-4 lg:grid-cols-[0.96fr,1.04fr]">
          <article className="editorial-card-primary rounded-[28px] p-6">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-foreground/72">
              市场饱和度
            </div>
            <p className="mt-3 text-[1.5rem] font-semibold leading-[1.4] text-primary-foreground md:text-[1.8rem]">
              {structured.market_health.competition_saturation.level}
            </p>
            <div className="mt-4 space-y-3 text-[0.98rem] leading-8 text-primary-foreground/78">
              {structured.market_health.competition_saturation.details.map(
                (detail) => (
                  <p key={detail} className="break-words">
                    {normalizeLine(detail)}
                  </p>
                )
              )}
              <p className="break-words">
                {structured.market_health.competition_saturation.interpretation}
              </p>
            </div>
          </article>

          <div className="space-y-4">
            <article className="editorial-card-secondary rounded-[26px] p-5 md:p-6">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                难题与攻略比
              </div>
              <p className="mt-3 text-[1.2rem] font-semibold leading-[1.5] text-foreground md:text-[1.32rem]">
                P/S 比约 {structured.market_health.ps_ratio.ratio}
              </p>
              <p className="mt-4 text-[0.98rem] leading-8 text-muted-foreground">
                {structured.market_health.ps_ratio.conclusion}
              </p>
              <p className="mt-2 text-[0.98rem] leading-8 text-muted-foreground">
                {structured.market_health.ps_ratio.interpretation}
              </p>
            </article>

            <article className="editorial-card-accent rounded-[26px] p-5 md:p-6">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                健康度判断
              </div>
              <p className="mt-3 text-[0.98rem] leading-8 text-muted-foreground">
                {structured.market_health.ps_ratio.health_assessment}
              </p>
            </article>
          </div>
        </div>
      </section>

      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={4}
          title={sectionTitles?.[4] ?? '核心战场推荐（画像分级）'}
          summary={SECTION_SUMMARIES[4]}
          termKey="battlefields"
        />
        <div className="mt-5 space-y-4">
          {structured.battlefields.map((battlefield, index) => (
            <article
              key={`${battlefield.name}-${index}`}
              className="editorial-card-secondary rounded-[26px] p-5 md:p-6"
            >
              <div className="flex flex-wrap items-center gap-3">
                <span className="editorial-order-badge text-xs">
                  Lv{index + 1}
                </span>
                <h3 className="min-w-0 break-words text-[1.15rem] font-semibold text-foreground md:text-[1.24rem]">
                  {battlefield.name}
                </h3>
              </div>
              <p className="mt-4 break-words text-[0.98rem] leading-8 text-muted-foreground">
                {battlefield.profile}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(battlefield.subreddits ?? []).map((subreddit) => (
                  <span
                    key={subreddit}
                    className="surface-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold"
                  >
                    {subreddit}
                  </span>
                ))}
              </div>
              {(battlefield.pain_points ?? []).length > 0 ? (
                <div className="mt-4 space-y-2 text-[0.98rem] leading-8 text-muted-foreground">
                  {(battlefield.pain_points ?? []).map((item) => (
                    <p key={item} className="break-words">
                      {normalizeLine(item)}
                    </p>
                  ))}
                </div>
              ) : null}
              <p className="mt-4 break-words text-[0.98rem] font-medium leading-8 text-foreground">
                {battlefield.strategy_advice}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={5}
          title={sectionTitles?.[5] ?? '用户痛点拆解'}
          summary={SECTION_SUMMARIES[5]}
        />
        <div className="mt-5 space-y-4">
          {structured.pain_points.map((painPoint, index) => {
            const evidenceLinks = buildPainEvidenceLinks(
              painPoint.evidence_chain,
              painEvidenceSources,
              index
            );
            return (
              <article
                key={`${painPoint.title}-${index}`}
                className="editorial-card-secondary rounded-[26px] p-5 md:p-6"
              >
                <h3 className="break-words text-[1.15rem] font-semibold text-foreground md:text-[1.24rem]">
                  {painPoint.title}
                </h3>
                {painPoint.data_impression ? (
                  <p className="mt-3 break-words text-[0.98rem] leading-8 text-muted-foreground">
                    {painPoint.data_impression}
                  </p>
                ) : null}
                <div className="mt-4 space-y-2 text-[0.98rem] leading-8 text-muted-foreground">
                  {painPoint.user_voices.map((voice) => (
                    <p key={voice} className="break-words">
                      {normalizeLine(voice)}
                    </p>
                  ))}
                </div>
                <p className="mt-4 break-words text-[0.98rem] font-medium leading-8 text-foreground">
                  {painPoint.interpretation}
                </p>
                {evidenceLinks.length > 0 ? (
                  <div className="mt-4 space-y-2">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                      证据链
                    </div>
                    {evidenceLinks.map((evidence) => (
                      <a
                        key={evidence.href}
                        href={evidence.href}
                        target="_blank"
                        rel="noreferrer"
                        className="block rounded-2xl border border-border/70 bg-background/82 px-4 py-3 transition-colors hover:border-primary/40 hover:bg-background"
                      >
                        <div className="text-sm font-medium text-foreground">
                          {evidence.label}
                        </div>
                        <div className="mt-1 text-sm leading-7 text-muted-foreground">
                          {evidence.text}
                        </div>
                      </a>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>

      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={6}
          title={sectionTitles?.[6] ?? '关键决策驱动力'}
          summary={SECTION_SUMMARIES[6]}
          termKey="drivers"
        />
        <div className="mt-5 space-y-4">
          {structured.drivers.map((driver, index) => (
            <article
              key={`${driver.title}-${index}`}
              className="editorial-card-accent rounded-[26px] p-5 md:p-6"
            >
              <h3 className="break-words text-[1.08rem] font-semibold text-foreground md:text-[1.16rem]">
                {driver.title}
              </h3>
              <p className="mt-3 break-words text-[0.98rem] leading-8 text-muted-foreground">
                {driver.description}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="editorial-frame rounded-[30px] p-6 md:p-7">
        <SectionHeading
          order={7}
          title={sectionTitles?.[7] ?? '商业机会'}
          summary={SECTION_SUMMARIES[7]}
          termKey="opportunities"
        />
        <div className="mt-5 space-y-4">
          {structured.opportunities.map((opportunity, index) => (
            <article
              key={`${opportunity.title}-${index}`}
              className="editorial-card-secondary rounded-[26px] p-5 md:p-6"
            >
              <h3 className="break-words text-[1.15rem] font-semibold text-foreground md:text-[1.24rem]">
                {opportunity.title}
              </h3>
              <p className="mt-3 break-words text-[0.98rem] leading-8 text-muted-foreground">
                {opportunity.product_positioning}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {opportunity.target_communities.map((community) => (
                  <span
                    key={community}
                    className="surface-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold"
                  >
                    {community}
                  </span>
                ))}
              </div>
              <div className="mt-4 space-y-2 text-[0.98rem] leading-8 text-muted-foreground">
                {opportunity.core_selling_points.map((point) => (
                  <p key={point} className="break-words">
                    {normalizeLine(point)}
                  </p>
                ))}
              </div>
              {opportunity.evidence_chain && opportunity.evidence_chain.length > 0 ? (
                <div className="mt-4 space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                    证据链
                  </div>
                  {opportunity.evidence_chain.map((evidence, evidenceIndex) => {
                    const href = normalizeRedditUrl(evidence.url);
                    const text = (evidence.title || '').trim();
                    if (!href || !text) return null;
                    return (
                      <a
                        key={`${href}-${evidenceIndex}`}
                        href={href}
                        target="_blank"
                        rel="noreferrer"
                        className="block rounded-2xl border border-border/70 bg-background/82 px-4 py-3 transition-colors hover:border-primary/40 hover:bg-background"
                      >
                        <div className="text-sm font-medium text-foreground">
                          {evidence.note || 'Reddit · 去 Reddit 看原帖'}
                        </div>
                        <div className="mt-1 text-sm leading-7 text-muted-foreground">
                          {text}
                        </div>
                      </a>
                    );
                  })}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};

export default StructuredReportSections;
