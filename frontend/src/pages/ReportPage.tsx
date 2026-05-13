/**
 * 商业洞察报告页 (Report Page)
 *
 * 基于 v0 设计还原 (insights-report.tsx)
 * 实现三视图状态机：Welcome -> Selector -> Detail
 * 包含后端数据适配器
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Download,
  Share2,
  TrendingUp,
  BarChart3,
  Target,
  Lightbulb,
  Users,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  Zap,
  Activity,
  ArrowRight,
  ChevronLeft,
  Sparkles,
  Plus,
  Trophy,
  FileText,
  Search,
} from 'lucide-react';
import clsx from 'clsx';

import { getAnalysisReport, getTaskSources } from '@/api/analyze.api';
import { isAuthenticated, logout } from '@/api/auth.api';
import StructuredReportSections from '@/components/report/StructuredReportSections';
import { ROUTES } from '@/router/routes';
import { ReportPageSkeleton } from '@/components/SkeletonLoader';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import SurfaceHero from '@/components/product/SurfaceHero';
import ProductStatePanel from '@/components/product/ProductStatePanel';
import DecisionSummaryPanel from '@/components/product/DecisionSummaryPanel';
import {
  buildReportActionPlan,
  buildReportDecisionSummary,
  buildReportSurfaceHero,
} from '@/lib/product-surface';
import { alignPainEvidenceSources } from '@/lib/report-evidence';
import { parseReportMarkdownSections } from '@/lib/report-markdown';
import { normalizeRedditUrl } from '@/lib/reddit-url';
import type { ReportResponse } from '@/types';

// ============================================================================
// Types & Interfaces (Matching v0 structure)
// ============================================================================

type DimensionKey =
  | 'marketHealth'
  | 'battlefields'
  | 'painPoints'
  | 'drivers'
  | 'opportunities';

interface DimensionInfo {
  key: DimensionKey;
  title: string;
  shortTitle: string;
  icon: React.ReactNode;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
  iconBgColor: string;
}

interface DecisionCard {
  title: string;
  conclusion: string;
  details: string[];
  icon: 'trending' | 'chart' | 'target' | 'lightbulb';
  iconColor: string;
  iconBgColor: string;
}

interface ReportData {
  decisionCards: DecisionCard[];
  marketHealth: {
    competitionSaturation: {
      level: string;
      details: string[];
      interpretation: string;
    };
    psRatio: {
      ratio: string;
      conclusion: string;
      interpretation: string;
      healthAssessment: string;
    };
  };
  battlefields: {
    name: string;
    subreddits: string[];
    profile: string;
    painPoints: string[];
    strategyAdvice: string;
  }[];
  painPoints: {
    emoji: string;
    title: string;
    userVoices: string[];
    dataImpression: string;
    interpretation: string;
    evidence: { text: string; url?: string; community?: string }[];
  }[];
  drivers: {
    title: string;
    description: string;
  }[];
  opportunities: {
    title: string;
    targetPainPoints: string[];
    targetCommunities: string[];
    productPositioning: string;
    coreSellingPoints: string[];
  }[];
}

const BASE_DIMENSIONS: DimensionInfo[] = [
  {
    key: 'marketHealth',
    title: '市场健康度诊断',
    shortTitle: '健康度',
    icon: <Activity className="w-6 h-6" />,
    description:
      '诊断市场竞争饱和度与问题/解决方案比例，判断市场成熟度与机会空间',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    iconBgColor: 'bg-blue-100',
  },
  {
    key: 'battlefields',
    title: '核心战场推荐',
    shortTitle: '战场',
    icon: <Target className="w-6 h-6" />,
    description: '锁定 4 个高潜力社群，了解用户画像、常见痛点与进入策略建议',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    iconBgColor: 'bg-purple-100',
  },
  {
    key: 'painPoints',
    title: '用户痛点洞察',
    shortTitle: '痛点',
    icon: <AlertTriangle className="w-6 h-6" />,
    description: '倾听用户真实声音，发现 3 个最常见且与产品直接相关的核心痛点',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    iconBgColor: 'bg-orange-100',
  },
  {
    key: 'drivers',
    title: 'Top 购买驱动力',
    shortTitle: '驱动力',
    icon: <Zap className="w-6 h-6" />,
    description: '掌握用户真正想要的 3 大核心价值，理解购买决策的关键驱动因素',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    iconBgColor: 'bg-green-100',
  },
  {
    key: 'opportunities',
    title: '商业机会',
    shortTitle: '机会',
    icon: <Lightbulb className="w-6 h-6" />,
    description: '2 张清晰的机会卡，结合痛点和驱动力，指明可执行的产品方向',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    iconBgColor: 'bg-amber-100',
  },
];

const REPORT_EMPTY_DIMENSION_COPY: Record<
  Exclude<DimensionKey, 'marketHealth'>,
  string
> = {
  battlefields: '先看现有社区分布，深挖时再补完整画像。',
  painPoints: '先看主要抱怨方向，深挖时再补完整痛点链。',
  drivers: '先看用户在意什么，深挖时再补完整驱动力。',
  opportunities: '先看机会方向，深挖时再补完整机会卡。',
};

const toUserFacingReportError = (error: unknown): string => {
  const message = error instanceof Error ? error.message : '';
  if (message === 'Missing canonical_report_json') {
    return '这份报告还在整理中，先重新加载一次。';
  }
  return '这份报告刚才没整理完整，先重新加载一次。';
};

// ============================================================================
// Adaptor: Backend -> Frontend Data Transformation
// ============================================================================

function adaptReportData(backendReport: ReportResponse): ReportData {
  const structured = backendReport.canonical_report_json;
  if (!structured) {
    throw new Error('Missing canonical_report_json');
  }
  const painPoints = alignPainEvidenceSources(
    structured.pain_points,
    backendReport.report.pain_points || []
  );

  const buildEvidence = (index: number) => {
    const structuredEvidence = structured.pain_points[index]?.evidence_chain || [];
    if (structuredEvidence.length > 0) {
      return structuredEvidence
        .map((item) => {
          const url = normalizeRedditUrl(item.url || undefined);
          const text = (item.title || '').trim();
          if (!url || !text) return null;
          return {
            text: text.length > 140 ? `${text.slice(0, 140)}…` : text,
            url,
            community: item.note,
          };
        })
        .filter(Boolean) as { text: string; url?: string; community?: string }[];
    }
    const examples = painPoints[index]?.example_posts || [];
    return examples
      .map((post) => {
        const url = normalizeRedditUrl(post.url, post.permalink);
        const text = (post.content || '').trim();
        if (!url || !text) return null;
        return {
          text: text.length > 140 ? `${text.slice(0, 140)}…` : text,
          url,
          community: post.community,
        };
      })
      .filter(Boolean) as { text: string; url?: string; community?: string }[];
  };

  return {
    decisionCards: structured.decision_cards.map((card) => ({
      title: card.title,
      conclusion: card.conclusion,
      details: card.details,
      icon: card.title.includes('趋势')
        ? 'trending'
        : card.title.includes('比例')
          ? 'chart'
          : card.title.includes('社群')
            ? 'target'
            : 'lightbulb',
      iconColor: 'text-primary',
      iconBgColor: 'bg-primary/10',
    })),
    marketHealth: {
      competitionSaturation: {
        level: structured.market_health.competition_saturation.level,
        details: structured.market_health.competition_saturation.details,
        interpretation:
          structured.market_health.competition_saturation.interpretation,
      },
      psRatio: {
        ratio: structured.market_health.ps_ratio.ratio,
        conclusion: structured.market_health.ps_ratio.conclusion,
        interpretation: structured.market_health.ps_ratio.interpretation,
        healthAssessment: structured.market_health.ps_ratio.health_assessment,
      },
    },
    battlefields: structured.battlefields.map((bf) => ({
      name: bf.name,
      subreddits: bf.subreddits.map((s) => (s.startsWith('r/') ? s : `r/${s}`)),
      profile: bf.profile,
      painPoints: bf.pain_points || [],
      strategyAdvice: bf.strategy_advice,
    })),
    painPoints: structured.pain_points.map((p, idx) => ({
      emoji: '😠',
      title: p.title,
      userVoices: p.user_voices,
      dataImpression: p.data_impression || '',
      interpretation: p.interpretation,
      evidence: buildEvidence(idx),
    })),
    drivers: structured.drivers.map((d) => ({
      title: d.title,
      description: d.description,
    })),
    opportunities: structured.opportunities.map((o) => ({
      title: o.title,
      targetPainPoints: o.target_pain_points,
      targetCommunities: o.target_communities,
      productPositioning: o.product_positioning,
      coreSellingPoints: o.core_selling_points,
    })),
    _rawMarkdown: backendReport.report_markdown,
    _rawHtml: backendReport.report_html,
  } as ReportData & { _rawHtml?: string | null; _rawMarkdown?: string | null };
}

// ============================================================================
// Component Implementation
// ============================================================================

const ReportPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [reportResponse, setReportResponse] = useState<ReportResponse | null>(
    null
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<
    'welcome' | 'selector' | 'detail' | 'full-report'
  >('welcome');
  const [selectedDimension, setSelectedDimension] =
    useState<DimensionKey | null>(null);
  const [viewedDimensions, setViewedDimensions] = useState<Set<DimensionKey>>(
    new Set()
  );
  const [showCelebration, setShowCelebration] = useState(false);

  const dimensions = useMemo(() => {
    const counts = {
      battlefields: reportData?.battlefields.length ?? 0,
      painPoints: reportData?.painPoints.length ?? 0,
      drivers: reportData?.drivers.length ?? 0,
      opportunities: reportData?.opportunities.length ?? 0,
    };

    const buildCountDescription = (
      count: number,
      withCount: (value: number) => string,
      emptyState: string
    ) => (count > 0 ? withCount(count) : emptyState);

    return BASE_DIMENSIONS.map((dim) => {
      switch (dim.key) {
        case 'battlefields':
          return {
            ...dim,
            description: buildCountDescription(
              counts.battlefields,
              (value) =>
                `锁定 ${value} 个高潜力社群，了解用户画像、常见痛点与进入策略建议`,
              REPORT_EMPTY_DIMENSION_COPY.battlefields
            ),
          };
        case 'painPoints':
          return {
            ...dim,
            description: buildCountDescription(
              counts.painPoints,
              (value) =>
                `倾听用户真实声音，发现 ${value} 个最常见且与产品直接相关的核心痛点`,
              REPORT_EMPTY_DIMENSION_COPY.painPoints
            ),
          };
        case 'drivers':
          return {
            ...dim,
            description: buildCountDescription(
              counts.drivers,
              (value) =>
                `掌握用户真正想要的 ${value} 大核心价值，理解购买决策的关键驱动因素`,
              REPORT_EMPTY_DIMENSION_COPY.drivers
            ),
          };
        case 'opportunities':
          return {
            ...dim,
            description: buildCountDescription(
              counts.opportunities,
              (value) =>
                `${value} 张清晰的机会卡，结合痛点和驱动力，指明可执行的产品方向`,
              REPORT_EMPTY_DIMENSION_COPY.opportunities
            ),
          };
        default:
          return dim;
      }
    });
  }, [reportData]);

  const loadReport = useCallback(async () => {
    if (!taskId) return;
    try {
      setLoading(true);
      setErrorMessage(null);
      const reportResponse = await getAnalysisReport(taskId);
      setReportResponse(reportResponse);
      setReportData(adaptReportData(reportResponse));
      void getTaskSources(taskId).catch(() => null);
    } catch (err) {
      console.error('Failed to load report', err);
      setReportResponse(null);
      setErrorMessage(toUserFacingReportError(err));
      setReportData(null);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) {
      navigate(ROUTES.HOME);
      return;
    }
    void loadReport();
  }, [taskId, navigate, loadReport]);

  /* Removed automatic celebration effect to avoid premature triggering */

  const handleCompleteExploration = () => {
    setShowCelebration(true);
    setTimeout(() => {
      setShowCelebration(false);
      setCurrentView('selector');
    }, 3000);
  };

  const handleSelectDimension = (key: DimensionKey) => {
    setSelectedDimension(key);
    setViewedDimensions((prev) => new Set([...prev, key]));
    setCurrentView('detail');
  };

  const handleNextDimension = () => {
    if (!selectedDimension) return;
    const currentIndex = dimensions.findIndex(
      (d) => d.key === selectedDimension
    );
    const nextIndex = (currentIndex + 1) % dimensions.length;
    const nextKey = dimensions[nextIndex]?.key;
    if (nextKey) handleSelectDimension(nextKey);
  };

  const handlePrevDimension = () => {
    if (!selectedDimension) return;
    const currentIndex = dimensions.findIndex(
      (d) => d.key === selectedDimension
    );
    const prevIndex =
      currentIndex === 0 ? dimensions.length - 1 : currentIndex - 1;
    const prevKey = dimensions[prevIndex]?.key;
    if (prevKey) handleSelectDimension(prevKey);
  };

  const handleLogout = () => {
    logout();
    window.location.reload();
  };

  const handleOpenFullReport = () => {
    if (reportResponse?.canonical_report_json) {
      setCurrentView('full-report');
      return;
    }
    const { _rawHtml: html, _rawMarkdown: markdown } =
      reportData as ReportData & {
        _rawHtml?: string | null;
        _rawMarkdown?: string | null;
      };
    if (html || markdown) {
      setCurrentView('full-report');
      return;
    }
    setCurrentView('selector');
  };

  const reportHero = reportResponse
    ? buildReportSurfaceHero(reportResponse)
    : null;
  const reportDecisionSummary = reportResponse
    ? buildReportDecisionSummary(reportResponse)
    : null;
  const reportActionPlan = reportResponse
    ? buildReportActionPlan(reportResponse)
    : null;
  const isDirectionalReport =
    reportActionPlan?.primaryIntent === 'restart-analysis';

  const handleRestartAnalysis = useCallback(() => {
    const description = reportResponse?.product_description?.trim() ?? '';
    const hint =
      reportActionPlan?.primaryIntent === 'restart-analysis'
        ? '已带回你刚才看的方向。先改成更贴近用户原话，再重跑。'
        : '已带回你刚才看的方向。直接在原描述上扩展后重跑。';

    navigate(ROUTES.HOME, {
      state: {
        prefillProductDescription: description,
        prefillSource: 'report',
        prefillHint: hint,
      },
    });
  }, [
    navigate,
    reportActionPlan?.primaryIntent,
    reportResponse?.product_description,
  ]);

  const handlePrimaryReportAction = useCallback(() => {
    if (reportActionPlan?.primaryIntent === 'restart-analysis') {
      handleRestartAnalysis();
      return;
    }
    handleOpenFullReport();
  }, [handleRestartAnalysis, reportActionPlan?.primaryIntent]);

  const reportFollowUpActions = useMemo(
    () =>
      reportActionPlan
        ? [
            {
              label: reportActionPlan.primaryLabel,
              onClick: handlePrimaryReportAction,
              tone: 'primary' as const,
            },
          ]
        : [],
    [handlePrimaryReportAction, reportActionPlan]
  );
  const reportDecisionCards = useMemo(
    () =>
      reportData?.decisionCards.slice(0, 3).map((card) => ({
        ...card,
        summary: card.details[0] || card.conclusion,
      })) ?? [],
    [reportData]
  );
  const fullReportSections = useMemo(
    () => parseReportMarkdownSections(reportResponse?.report_markdown),
    [reportResponse?.report_markdown]
  );
  const fullReportSectionMap = useMemo(
    () =>
      new Map(fullReportSections.map((section) => [section.order, section])),
    [fullReportSections]
  );
  const alignedPainEvidenceSources = useMemo(
    () =>
      reportResponse?.canonical_report_json
        ? alignPainEvidenceSources(
            reportResponse.canonical_report_json.pain_points,
            reportResponse.report?.pain_points ?? []
          )
        : [],
    [reportResponse]
  );
  const fullReportOverviewLead =
    reportResponse?.product_description?.trim() ??
    reportResponse?.canonical_report_json?.decision_cards?.[0]?.conclusion ??
    '先把这次判断最核心的矛盾、机会和切入点看清。';
  const fullReportOverviewDetails = [
    reportResponse?.canonical_report_json?.decision_cards?.[0]?.conclusion,
    reportResponse?.canonical_report_json?.decision_cards?.[2]?.conclusion,
    reportResponse?.canonical_report_json?.opportunities?.[0]
      ?.product_positioning,
  ].filter(Boolean) as string[];
  const normalizedFullReportOverviewDetails =
    fullReportOverviewDetails.length > 0
      ? fullReportOverviewDetails
      : ['先把赛道、人群和主判断摆清楚，后面的战场、痛点和机会才有参照。'];
  const fullReportSectionTitles = {
    1: fullReportSectionMap.get(1)?.title,
    2: fullReportSectionMap.get(2)?.title,
    3: fullReportSectionMap.get(3)?.title,
    4: fullReportSectionMap.get(4)?.title,
    5: fullReportSectionMap.get(5)?.title,
    6: fullReportSectionMap.get(6)?.title,
    7: fullReportSectionMap.get(7)?.title,
  };

  const getCardIcon = (icon: string) => {
    switch (icon) {
      case 'trending':
        return <TrendingUp className="w-5 h-5" />;
      case 'chart':
        return <BarChart3 className="w-5 h-5" />;
      case 'target':
        return <Target className="w-5 h-5" />;
      case 'lightbulb':
        return <Lightbulb className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  };

  if (loading) {
    return <ReportPageSkeleton />;
  }

  if (errorMessage) {
    return (
      <div className="min-h-screen bg-background">
        <header className="surface-header sticky top-0 z-10 border-b border-border">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="surface-brand-mark flex h-8 w-8 items-center justify-center rounded-lg">
                <Search className="w-5 h-5 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-semibold text-foreground">
                Reddit 商业信号扫描器
              </h1>
            </div>
            <button
              type="button"
              onClick={() => navigate(ROUTES.HOME)}
              className="surface-action-secondary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors"
            >
              返回首页
            </button>
          </div>
        </header>
        <main className="container mx-auto px-4 py-16">
          <div className="mx-auto max-w-2xl">
            <ProductStatePanel
              tone="error"
              title="这份结果还在整理中"
              description={errorMessage}
              nextStep="先重载一次；还不行就回首页重跑。"
              actions={[
                { label: '重新加载', onClick: loadReport, tone: 'primary' },
                { label: '返回首页', onClick: () => navigate(ROUTES.HOME) },
              ]}
            />
          </div>
        </main>
      </div>
    );
  }

  if (!reportData) {
    return <ReportPageSkeleton />;
  }

  const currentDimensionInfo = dimensions.find(
    (d) => d.key === selectedDimension
  );

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <header className="surface-header sticky top-0 z-10 border-b border-border">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="surface-brand-mark flex h-9 w-9 items-center justify-center rounded-xl">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <div className="surface-section-kicker">Signal Desk</div>
              <h1 className="text-xl font-semibold text-foreground">
                Reddit 商业信号扫描器
              </h1>
            </div>
          </div>
          <div className="flex gap-2">
            {isAuthenticated() && (
              <button
                type="button"
                onClick={handleLogout}
                className="surface-action-secondary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors"
              >
                退出登录
              </button>
            )}
            <button
              type="button"
              className="surface-action-secondary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors"
            >
              <Share2 className="w-4 h-4 mr-2" />
              分享报告
            </button>
            <button
              type="button"
              className="surface-action-primary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors"
            >
              <Download className="w-4 h-4 mr-2" />
              导出 PDF
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
        <NavigationBreadcrumb currentStep="report" canNavigateBack={false} />

        {reportHero ? (
          <div className="mx-auto mb-8 max-w-6xl">
            <SurfaceHero {...reportHero} />
          </div>
        ) : null}

        {/* Celebration Overlay */}
        {showCelebration && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm animate-in fade-in zoom-in duration-300">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center mx-auto animate-bounce">
                <Trophy className="w-10 h-10 text-primary-foreground" />
              </div>
              <h2 className="text-2xl font-bold text-foreground">
                恭喜完成全部探索！
              </h2>
              <p className="text-muted-foreground">
                你已查看所有 5 个维度的洞察
              </p>
            </div>
          </div>
        )}

        {/* WELCOME VIEW */}
        {currentView === 'welcome' && (
          <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-500">
            {reportDecisionSummary ? (
              <DecisionSummaryPanel
                title={isDirectionalReport ? '这轮先拍小板' : '先拍第一板'}
                verdictTitle={reportDecisionSummary.verdictTitle}
                verdictDescription={reportDecisionSummary.verdictDescription}
                reasonsTitle="拍板依据"
                reasons={reportDecisionSummary.reasons}
                signals={reportDecisionSummary.signals}
                nextStepDescription={reportDecisionSummary.nextStepDescription}
              />
            ) : null}

            <div className="space-y-3">
              <div className="space-y-2">
                <div className="surface-section-kicker">先看信号</div>
                <h2 className="text-2xl font-semibold text-foreground">
                  支持拍板的 3 条证据
                </h2>
                <p className="text-sm leading-6 text-muted-foreground">
                  先把最能支撑拍板的三条信号看完。
                </p>
              </div>
              <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                {reportDecisionCards.map((card, index) => (
                  <div
                    key={index}
                    className="surface-panel-muted rounded-[24px] p-5"
                  >
                    <div className="flex gap-3">
                      <div
                        className={clsx(
                          'w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0',
                          card.iconBgColor,
                          card.iconColor
                        )}
                      >
                        {getCardIcon(card.icon)}
                      </div>
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-muted-foreground">
                          {card.title}
                        </p>
                        <h3 className="text-base font-semibold text-foreground leading-snug">
                          {card.conclusion}
                        </h3>
                        <p className="text-sm text-muted-foreground leading-6">
                          {card.summary}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-panel relative overflow-hidden rounded-[28px] p-8">
              <div className="absolute top-0 right-0 h-64 w-64 rounded-full bg-primary/8 blur-3xl -translate-y-1/2 translate-x-1/2" />
              <div className="absolute bottom-0 left-0 h-48 w-48 rounded-full bg-secondary/10 blur-3xl translate-y-1/2 -translate-x-1/2" />

              <div className="relative z-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="space-y-2">
                  <div className="surface-section-kicker">
                    <Sparkles className="h-3.5 w-3.5" />
                    {reportActionPlan?.sectionEyebrow ?? '深读入口'}
                  </div>
                  <h2 className="max-w-3xl text-xl font-semibold text-foreground">
                    {reportActionPlan?.sectionTitle ??
                      '完整结论已经整理好，适合直接往下拍板'}
                  </h2>
                  <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                    {reportActionPlan?.sectionDescription ??
                      '这里给你完整判断、关键依据和可落地动作，不再解释分析过程。'}
                  </p>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={handlePrimaryReportAction}
                    className="surface-action-primary inline-flex items-center justify-center rounded-xl px-5 py-2.5 text-sm font-medium transition-colors"
                  >
                    {reportActionPlan?.primaryLabel ?? '看完整报告'}{' '}
                    <FileText className="ml-2 h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrentView('selector')}
                    className="surface-action-secondary inline-flex items-center justify-center rounded-xl px-5 py-2.5 text-sm font-medium transition-colors"
                  >
                    {reportActionPlan?.secondaryLabel ?? '逐维探索'}{' '}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SELECTOR VIEW */}
        {currentView === 'selector' && (
          <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-right-4 duration-500">
            {viewedDimensions.size > 0 && (
              <div className="surface-panel-muted flex items-center justify-between rounded-2xl p-4">
                <div className="text-sm text-muted-foreground">
                  探索进度：
                  <span className="font-semibold text-foreground">
                    {viewedDimensions.size}
                  </span>{' '}
                  / {dimensions.length} 个维度
                </div>
                <div className="flex gap-2">
                  {dimensions.map((dim) => (
                    <div
                      key={dim.key}
                      className={clsx(
                        'h-3 w-3 rounded-full transition-[transform,background-color]',
                        viewedDimensions.has(dim.key)
                          ? 'bg-primary scale-110'
                          : 'bg-muted-foreground/30'
                      )}
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="text-center space-y-2">
              <div className="surface-section-kicker justify-center">
                逐维拆判断
              </div>
              <h2 className="text-2xl font-semibold text-foreground">
                继续拆证据
              </h2>
              <p className="text-muted-foreground">
                先看你最想确认的一块，不用五个维度一起读。
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {dimensions.map((dim) => (
                <button
                  type="button"
                  key={dim.key}
                  onClick={() => handleSelectDimension(dim.key)}
                  className={clsx(
                    'group relative text-left p-6 rounded-[24px] border transition-[transform,box-shadow,border-color] duration-300 hover:scale-[1.01] hover:shadow-editorial',
                    dim.bgColor,
                    dim.borderColor,
                    'hover:border-primary'
                  )}
                >
                  {viewedDimensions.has(dim.key) && (
                    <div className="absolute -top-2 -right-2 bg-background rounded-full px-2 py-0.5 border text-xs font-medium shadow flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> 已查看
                    </div>
                  )}
                  <div className="flex items-start gap-4">
                    <div
                      className={clsx(
                        'w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform',
                        dim.iconBgColor,
                        dim.color
                      )}
                    >
                      {dim.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-foreground text-lg mb-2 group-hover:text-primary transition-colors">
                        {dim.title}
                      </h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {dim.description}
                      </p>
                    </div>
                  </div>
                  <div className="absolute right-4 bottom-4 opacity-0 group-hover:opacity-100 transition-opacity text-primary">
                    <ArrowRight className="w-5 h-5" />
                  </div>
                </button>
              ))}

              <button
                type="button"
                onClick={() => navigate(ROUTES.HOME)}
                className="group surface-panel-muted flex min-h-[160px] flex-col items-center justify-center rounded-[24px] border border-dashed border-muted-foreground/30 p-6 text-left transition-[transform,border-color,background-color] duration-300 hover:border-primary/50 hover:bg-muted/30"
              >
                <div className="w-14 h-14 rounded-xl bg-muted/50 flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                  <Plus className="w-7 h-7 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <h3 className="font-semibold text-muted-foreground group-hover:text-foreground transition-colors">
                  新建分析
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  分析其他产品方向
                </p>
              </button>

              {/* View Full Report Card */}
              {reportData && (
                <button
                  type="button"
                  onClick={handleOpenFullReport}
                  className="group surface-panel-muted flex min-h-[160px] flex-col items-center justify-center rounded-[24px] border border-dashed border-muted-foreground/30 p-6 text-left transition-[transform,border-color,background-color] duration-300 hover:border-primary/50 hover:bg-muted/30"
                >
                  <div className="w-14 h-14 rounded-xl bg-muted/50 flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                    <FileText className="w-7 h-7 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <h3 className="font-semibold text-muted-foreground group-hover:text-foreground transition-colors">
                    完整报告
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    查看完整报告
                  </p>
                </button>
              )}
            </div>

            <div className="text-center">
              <button
                type="button"
                onClick={() => setCurrentView('welcome')}
                className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-colors"
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                返回查看决策卡片
              </button>
            </div>
          </div>
        )}

        {currentView === 'full-report' && (
          <div className="mx-auto max-w-5xl space-y-6 animate-in slide-in-from-right-4 duration-500">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setCurrentView('welcome')}
                className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-colors"
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                返回判断页
              </button>
              <button
                type="button"
                onClick={() => setCurrentView('selector')}
                className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-colors"
              >
                逐维探索
                <ArrowRight className="ml-2 h-4 w-4" />
              </button>
            </div>

            <section className="surface-panel rounded-[28px] p-6 md:p-8">
              <div className="space-y-2">
                <div className="surface-section-kicker">完整报告</div>
                <h2 className="text-[1.6rem] font-semibold leading-tight text-foreground md:text-[1.95rem]">
                  和卡片同一颗粒度的完整正文
                </h2>
                <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
                  完整正文按同一套 1 到 7 结构展开，适合把依据和动作一次看完。
                </p>
              </div>

              {reportResponse?.canonical_report_json ? (
                <StructuredReportSections
                  className="mt-8"
                  structured={reportResponse.canonical_report_json}
                  overviewLead={fullReportOverviewLead}
                  overviewDetails={normalizedFullReportOverviewDetails}
                  painEvidenceSources={alignedPainEvidenceSources}
                  sectionTitles={fullReportSectionTitles}
                />
              ) : null}
            </section>
          </div>
        )}

        {/* DETAIL VIEW */}
        {currentView === 'detail' && currentDimensionInfo && (
          <div className="max-w-4xl mx-auto space-y-6 animate-in slide-in-from-right-8 duration-500">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setCurrentView('selector')}
                className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                返回维度选择
              </button>
              <div className="flex gap-1">
                {dimensions.map((dim) => (
                  <div
                    key={dim.key}
                    className={clsx(
                      'w-2.5 h-2.5 rounded-full',
                      dim.key === selectedDimension
                        ? 'bg-primary scale-125'
                        : viewedDimensions.has(dim.key)
                          ? 'bg-primary/40'
                          : 'bg-muted'
                    )}
                  />
                ))}
              </div>
            </div>

            <div
              className={clsx(
                'rounded-xl p-6 border-2 flex items-center gap-4',
                currentDimensionInfo.bgColor,
                currentDimensionInfo.borderColor
              )}
            >
              <div
                className={clsx(
                  'w-14 h-14 rounded-xl flex items-center justify-center',
                  currentDimensionInfo.iconBgColor,
                  currentDimensionInfo.color
                )}
              >
                {currentDimensionInfo.icon}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  {currentDimensionInfo.title}
                </h2>
                <p className="text-muted-foreground">
                  {currentDimensionInfo.description}
                </p>
              </div>
            </div>

            {/* Dynamic Content Rendering based on Dimension */}
            {selectedDimension === 'marketHealth' && (
              <div className="space-y-6">
                <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                  <h3 className="font-semibold flex items-center gap-2 text-lg">
                    <Activity className="w-5 h-5 text-blue-600" />{' '}
                    竞争饱和度分析
                  </h3>
                  <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
                    <span className="font-medium">综合判断</span>
                    <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded text-xs font-semibold">
                      {reportData.marketHealth.competitionSaturation.level}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground">依据：</p>
                    {reportData.marketHealth.competitionSaturation.details.map(
                      (d, i) => (
                        <div key={i} className="flex gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                          {d}
                        </div>
                      )
                    )}
                  </div>
                </div>
                <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                  <h3 className="font-semibold flex items-center gap-2 text-lg">
                    <BarChart3 className="w-5 h-5 text-primary" /> P/S Ratio
                  </h3>
                  <div className="flex items-center justify-between p-4 bg-primary/5 rounded-lg">
                    <span className="font-medium">比率</span>
                    <span className="text-2xl font-bold text-primary">
                      {reportData.marketHealth.psRatio.ratio}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {reportData.marketHealth.psRatio.interpretation}
                  </p>
                </div>
              </div>
            )}

            {selectedDimension === 'battlefields' && (
              <div className="space-y-4">
                {reportData.battlefields.length > 0 ? (
                  reportData.battlefields.map((bf, i) => (
                    <div
                      key={i}
                      className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4"
                    >
                      <div className="flex items-center gap-2">
                        <Users className="w-5 h-5 text-purple-600" />
                        <h3 className="font-bold text-lg">{bf.name}</h3>
                      </div>
                      <div className="flex gap-2">
                        {bf.subreddits.map((s) => (
                          <span
                            key={s}
                            className="bg-secondary px-2 py-1 rounded text-xs text-secondary-foreground"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                      <div className="p-3 bg-muted/50 rounded-lg text-sm">
                        <span className="font-medium block mb-1">画像</span>{' '}
                        {bf.profile}
                      </div>
                      <div className="p-3 bg-primary/5 rounded-lg border border-primary/20 text-sm">
                        <span className="font-medium block mb-1 text-primary">
                          策略建议
                        </span>{' '}
                        {bf.strategyAdvice}
                      </div>
                    </div>
                  ))
                ) : (
                  <ProductStatePanel
                    tone="empty"
                    compact
                    title="先把方向判断出来就够了"
                    description={REPORT_EMPTY_DIMENSION_COPY.battlefields}
                    nextStep="觉得有价值就补跑完整报告，或先扩大社区范围。"
                    actions={reportFollowUpActions}
                  />
                )}
              </div>
            )}

            {/* Placeholder for other dimensions logic (simplified for length, adapt as needed) */}
            {selectedDimension === 'painPoints' && (
              <div className="space-y-4">
                {reportData.painPoints.length > 0 ? (
                  reportData.painPoints.map((p, i) => (
                    <div
                      key={i}
                      className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4"
                    >
                      <div className="flex items-center gap-2 text-xl font-bold">
                        <span>{p.emoji}</span> {p.title}
                      </div>
                      <div className="space-y-2">
                        {p.userVoices.map((v, idx) => (
                          <div
                            key={idx}
                            className="flex gap-2 p-3 bg-muted/50 rounded-lg text-sm italic text-muted-foreground"
                          >
                            <MessageSquare className="w-4 h-4 mt-1 flex-shrink-0 text-primary" />{' '}
                            {v}
                          </div>
                        ))}
                      </div>
                      {p.dataImpression && (
                        <div className="p-3 bg-muted/40 text-sm rounded-lg">
                          <span className="font-medium">数据印象：</span>{' '}
                          {p.dataImpression}
                        </div>
                      )}
                      <div className="p-3 bg-blue-50 text-blue-700 text-sm rounded-lg">
                        <span className="font-medium">解读：</span>{' '}
                        {p.interpretation}
                      </div>
                      {p.evidence.length > 0 ? (
                        <div className="space-y-2 text-sm">
                          <div className="font-medium text-muted-foreground">
                            证据溯源：
                          </div>
                          <div className="space-y-2">
                            {p.evidence.map((ev, idx) =>
                              ev.url ? (
                                <a
                                  key={`${ev.url}-${idx}`}
                                  href={ev.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="block rounded-lg border border-dashed border-muted-foreground/40 p-3 hover:border-primary/60 hover:bg-muted/30 transition-colors"
                                >
                                  <div className="text-xs text-muted-foreground mb-1">
                                    {ev.community
                                      ? `社区：${ev.community}`
                                      : '社区：未知'}
                                  </div>
                                  <div className="text-sm text-foreground">
                                    {ev.text}
                                  </div>
                                </a>
                              ) : (
                                <div
                                  key={idx}
                                  className="block rounded-lg border border-dashed border-muted-foreground/40 p-3 bg-muted/10"
                                >
                                  <div className="text-xs text-muted-foreground mb-1">
                                    {ev.community
                                      ? `社区：${ev.community}`
                                      : '社区：未知'}
                                  </div>
                                  <div className="text-sm text-foreground">
                                    {ev.text}
                                  </div>
                                  <div className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" />{' '}
                                    这条原话已经保留下来，原帖跳转会在继续深挖时自动补齐
                                  </div>
                                </div>
                              )
                            )}
                          </div>
                        </div>
                      ) : (
                        <ProductStatePanel
                          tone="empty"
                          compact
                          title="先看结论和解读就够了"
                          description="这块已够判断方向，深挖时再补完整原帖与引用。"
                          nextStep="先定追不追；要追就补跑完整报告。"
                          actions={reportFollowUpActions}
                        />
                      )}
                    </div>
                  ))
                ) : (
                  <ProductStatePanel
                    tone="empty"
                    compact
                    title="先看方向，不急着等完整痛点清单"
                    description={REPORT_EMPTY_DIMENSION_COPY.painPoints}
                    nextStep="觉得值得追，再补跑完整报告补齐痛点链。"
                    actions={reportFollowUpActions}
                  />
                )}
              </div>
            )}

            {selectedDimension === 'drivers' && (
              <div className="space-y-4">
                {reportData.drivers.length > 0 ? (
                  reportData.drivers.map((d, i) => (
                    <div
                      key={i}
                      className="rounded-xl border bg-card text-card-foreground shadow-sm p-6"
                    >
                      <h3 className="font-bold text-lg flex items-center gap-2 mb-2">
                        <CheckCircle2 className="w-5 h-5 text-green-600" />{' '}
                        {d.title}
                      </h3>
                      <p className="text-muted-foreground">{d.description}</p>
                    </div>
                  ))
                ) : (
                  <ProductStatePanel
                    tone="empty"
                    compact
                    title="先看用户反应，再补驱动力"
                    description={REPORT_EMPTY_DIMENSION_COPY.drivers}
                    nextStep="先定方向；值得追再补跑完整报告。"
                    actions={reportFollowUpActions}
                  />
                )}
              </div>
            )}

            {selectedDimension === 'opportunities' && (
              <div className="space-y-4">
                {reportData.opportunities.length > 0 ? (
                  reportData.opportunities.map((o, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-amber-200 bg-amber-50/30 p-6 space-y-4"
                    >
                      <h3 className="font-bold text-lg flex items-center gap-2 text-amber-800">
                        <Lightbulb className="w-5 h-5" /> {o.title}
                      </h3>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium text-muted-foreground block mb-1">
                            定位
                          </span>
                          {o.productPositioning}
                        </div>
                        <div>
                          <span className="font-medium text-muted-foreground block mb-1">
                            卖点
                          </span>
                          <ul className="list-disc pl-4">
                            {o.coreSellingPoints.map((sp, idx) => (
                              <li key={idx}>{sp}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <ProductStatePanel
                    tone="empty"
                    compact
                    title="先判断有没有继续追的必要"
                    description={REPORT_EMPTY_DIMENSION_COPY.opportunities}
                    nextStep="先定追不追；要追就补跑完整报告补齐机会卡。"
                    actions={reportFollowUpActions}
                  />
                )}
              </div>
            )}

            <div className="flex items-center justify-between pt-6 border-t border-border">
              <button
                type="button"
                onClick={handlePrevDimension}
                className="surface-action-secondary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50"
                disabled={
                  dimensions.findIndex((d) => d.key === selectedDimension) === 0
                }
              >
                <ChevronLeft className="w-4 h-4 mr-2" /> 上一个维度
              </button>

              {dimensions.findIndex((d) => d.key === selectedDimension) ===
              dimensions.length - 1 ? (
                <button
                  type="button"
                  onClick={handleCompleteExploration}
                  className="surface-action-primary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors"
                >
                  完成探索 <CheckCircle2 className="w-4 h-4 ml-2" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleNextDimension}
                  className="surface-action-secondary inline-flex h-9 items-center justify-center rounded-xl px-3 text-sm font-medium transition-colors"
                >
                  下一个维度 <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ReportPage;
