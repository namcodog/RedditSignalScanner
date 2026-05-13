import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import { ChevronLeft, FileText, LayoutGrid } from 'lucide-react';

import StructuredReportSections from '@/components/report/StructuredReportSections';
import { alignPainEvidenceSources } from '@/lib/report-evidence';
import { parseReportMarkdownSections } from '@/lib/report-markdown';
import {
  buildStandardReportPrefillState,
  formatStandardSnapshotTime,
  loadStandardReportSnapshot,
  type StandardReportSnapshot,
} from '@/lib/standard-report';
import { ROUTES } from '@/router/routes';

const TABS = [
  { key: 'cards', label: '卡片版', icon: LayoutGrid },
  { key: 'report', label: '完整报告', icon: FileText },
] as const;

const StandardReportPage = () => {
  const navigate = useNavigate();
  const { slug = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [snapshot, setSnapshot] = useState<StandardReportSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeTab = searchParams.get('view') === 'report' ? 'report' : 'cards';

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const payload = await loadStandardReportSnapshot(slug);
        if (!active) return;
        setSnapshot(payload);
        setError(null);
      } catch {
        if (!active) return;
        setError('这份标准报告还没有落到前端，请先重新导出标准快照。');
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [slug]);

  const report = snapshot?.report ?? null;
  const structured = report?.canonical_report_json ?? null;

  const headerMetrics = useMemo(() => {
    if (!snapshot?.summary) return [];
    return [
      { label: '战场', value: String(snapshot.summary['battlefields'] ?? '-') },
      { label: '痛点', value: String(snapshot.summary['pain_points'] ?? '-') },
      { label: '驱动力', value: String(snapshot.summary['drivers'] ?? '-') },
      {
        label: '机会',
        value: String(snapshot.summary['opportunities'] ?? '-'),
      },
    ];
  }, [snapshot?.summary]);

  const markdownSections = useMemo(
    () => parseReportMarkdownSections(report?.report_markdown),
    [report?.report_markdown]
  );
  const markdownSectionMap = useMemo(
    () => new Map(markdownSections.map((section) => [section.order, section])),
    [markdownSections]
  );

  if (error) {
    return (
      <div className="min-h-screen bg-background px-4 py-10">
        <div className="mx-auto max-w-5xl rounded-[28px] surface-panel p-8">
          <button
            type="button"
            onClick={() => navigate(ROUTES.HOME)}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground"
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
            返回首页
          </button>
          <h1 className="mt-6 text-3xl font-semibold text-foreground">
            标准报告暂不可用
          </h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            {error}
          </p>
        </div>
      </div>
    );
  }

  if (!snapshot || !report || !structured) {
    return <div className="min-h-screen bg-background" />;
  }

  const reportPainPoints = alignPainEvidenceSources(
    structured.pain_points,
    report.report?.pain_points ?? []
  );
  const overviewLead = snapshot.prompt;
  const overviewDetails = [
    structured.decision_cards?.[0]?.conclusion,
    structured.decision_cards?.[2]?.conclusion,
    structured.opportunities?.[0]?.product_positioning,
  ].filter(Boolean) as string[];
  const normalizedOverviewDetails =
    overviewDetails.length > 0
      ? overviewDetails
      : ['先把赛道、人群和主判断摆清楚，后面的战场、痛点和机会才有参照。'];
  const sectionTitles = {
    1: markdownSectionMap.get(1)?.title,
    2: markdownSectionMap.get(2)?.title,
    3: markdownSectionMap.get(3)?.title,
    4: markdownSectionMap.get(4)?.title,
    5: markdownSectionMap.get(5)?.title,
    6: markdownSectionMap.get(6)?.title,
    7: markdownSectionMap.get(7)?.title,
  };

  return (
    <div className="editorial-shell min-h-screen bg-background px-4 py-8 md:py-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="surface-header editorial-frame rounded-[30px] px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => navigate(ROUTES.HOME)}
              className="inline-flex items-center gap-2 text-sm text-muted-foreground"
            >
              <ChevronLeft aria-hidden="true" className="h-4 w-4" />
              返回首页
            </button>
            <span className="surface-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold">
              固定标准报告 · 已校验{' '}
              {formatStandardSnapshotTime(snapshot.validated_at)}
            </span>
          </div>
        </header>

        <section className="editorial-frame overflow-hidden rounded-[34px] px-6 py-7 md:px-8 md:py-9">
          <div className="space-y-5">
            <div className="space-y-3">
              <div className="surface-section-kicker">Standard Report</div>
              <div className="surface-rule max-w-44" />
              <h1 className="max-w-4xl text-[2.35rem] font-semibold leading-[1.08] text-foreground md:text-[3.4rem]">
                {snapshot.title}
              </h1>
              <p className="max-w-4xl text-base leading-8 text-muted-foreground">
                {snapshot.prompt}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="surface-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold">
                固定标准结果
              </span>
              <span className="surface-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold">
                卡片与长报告同源
              </span>
              <span className="surface-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold">
                已校验 {formatStandardSnapshotTime(snapshot.validated_at)}
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {headerMetrics.map((metric) => (
                <div
                  key={metric.label}
                  className="editorial-metric rounded-[22px] px-4 py-4"
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    {metric.label}
                  </div>
                  <div className="surface-number mt-3 text-3xl font-semibold text-foreground">
                    {metric.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="editorial-frame rounded-[30px] p-4">
          <div className="flex flex-wrap gap-3">
            {TABS.map((tab) => {
              const selected = activeTab === tab.key;
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setSearchParams({ view: tab.key })}
                  className={clsx(
                    'inline-flex h-11 items-center gap-2 rounded-xl px-4 text-sm font-medium transition-colors',
                    selected ? 'editorial-tab-active' : 'editorial-tab'
                  )}
                >
                  <Icon aria-hidden="true" className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </section>

        {activeTab === 'cards' ? (
          <StructuredReportSections
            structured={structured}
            overviewLead={overviewLead}
            overviewDetails={normalizedOverviewDetails}
            painEvidenceSources={reportPainPoints}
            sectionTitles={sectionTitles}
          />
        ) : (
          <section className="editorial-frame rounded-[32px] p-6 md:p-8">
            <div className="mx-auto max-w-3xl">
              <div className="surface-section-kicker">完整报告</div>
              <h2 className="mt-4 text-[1.6rem] font-semibold leading-tight text-foreground md:text-[1.9rem]">
                和卡片同一颗粒度的完整正文
              </h2>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                完整正文保留同一套 1 到 7 结构，把判断依据和动作建议一次看清。
              </p>
              <StructuredReportSections
                className="mt-8"
                structured={structured}
                overviewLead={overviewLead}
                overviewDetails={normalizedOverviewDetails}
                painEvidenceSources={reportPainPoints}
                sectionTitles={sectionTitles}
              />
            </div>
          </section>
        )}

        <section className="editorial-card-primary rounded-[30px] p-6 md:p-7">
          <div className="surface-section-kicker text-primary-foreground/72">
            带回真实分析
          </div>
          <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
            <div>
              <h2 className="text-2xl font-semibold text-primary-foreground">
                别停在标准样板，回首页写你的真实问题
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-primary-foreground/78">
                这份标准报告已经帮你把成品长什么样说清了。下一步回首页直接写你的真实问题；输入框会保持空白，下面这题只当参考方向。
              </p>
            </div>
            <button
              type="button"
              onClick={() =>
                navigate(ROUTES.HOME, {
                  state: buildStandardReportPrefillState(snapshot.prompt, {
                    title: snapshot.title,
                  }),
                })
              }
              className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-white/16 bg-white/10 px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-white/16"
            >
              回首页写我的问题
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};

export default StandardReportPage;
