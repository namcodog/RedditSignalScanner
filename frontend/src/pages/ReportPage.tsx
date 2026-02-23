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
  LayoutGrid,
  FileText,
  FileWarning,
  Search,
} from 'lucide-react';
import clsx from 'clsx';

import { getAnalysisReport, getTaskSources } from '@/api/analyze.api';
import { isAuthenticated, logout } from '@/api/auth.api';
import { ROUTES } from '@/router';
import { ReportPageSkeleton } from '@/components/SkeletonLoader';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import type { ReportResponse } from '@/types';

// ============================================================================
// Types & Interfaces (Matching v0 structure)
// ============================================================================

type DimensionKey = "marketHealth" | "battlefields" | "painPoints" | "drivers" | "opportunities";

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
  icon: "trending" | "chart" | "target" | "lightbulb";
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
    key: "marketHealth",
    title: "市场健康度诊断",
    shortTitle: "健康度",
    icon: <Activity className="w-6 h-6" />,
    description: "诊断市场竞争饱和度与问题/解决方案比例，判断市场成熟度与机会空间",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    iconBgColor: "bg-blue-100",
  },
  {
    key: "battlefields",
    title: "核心战场推荐",
    shortTitle: "战场",
    icon: <Target className="w-6 h-6" />,
    description: "锁定 4 个高潜力社群，了解用户画像、常见痛点与进入策略建议",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
    iconBgColor: "bg-purple-100",
  },
  {
    key: "painPoints",
    title: "用户痛点洞察",
    shortTitle: "痛点",
    icon: <AlertTriangle className="w-6 h-6" />,
    description: "倾听用户真实声音，发现 3 个最常见且与产品直接相关的核心痛点",
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-200",
    iconBgColor: "bg-orange-100",
  },
  {
    key: "drivers",
    title: "Top 购买驱动力",
    shortTitle: "驱动力",
    icon: <Zap className="w-6 h-6" />,
    description: "掌握用户真正想要的 3 大核心价值，理解购买决策的关键驱动因素",
    color: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    iconBgColor: "bg-green-100",
  },
  {
    key: "opportunities",
    title: "商业机会",
    shortTitle: "机会",
    icon: <Lightbulb className="w-6 h-6" />,
    description: "2 张清晰的机会卡，结合痛点和驱动力，指明可执行的产品方向",
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
    iconBgColor: "bg-amber-100",
  },
];

// ============================================================================
// Adaptor: Backend -> Frontend Data Transformation
// ============================================================================

function adaptReportData(backendReport: ReportResponse): ReportData {
  const painPoints = backendReport.report.pain_points || [];
  const structured = backendReport.report_structured;
  if (!structured) {
    throw new Error("Missing report_structured");
  }

  const buildEvidence = (index: number) => {
    const examples = painPoints[index]?.example_posts || [];
    return examples
      .map((post) => {
        const url = post.url || post.permalink || undefined;
        const text = (post.content || "").trim();
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
      icon: card.title.includes("趋势") ? "trending" : card.title.includes("比例") ? "chart" : card.title.includes("社群") ? "target" : "lightbulb",
      iconColor: "text-primary",
      iconBgColor: "bg-primary/10",
    })),
    marketHealth: {
      competitionSaturation: {
        level: structured.market_health.competition_saturation.level,
        details: structured.market_health.competition_saturation.details,
        interpretation: structured.market_health.competition_saturation.interpretation,
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
      subreddits: bf.subreddits.map((s) => (s.startsWith("r/") ? s : `r/${s}`)),
      profile: bf.profile,
      painPoints: bf.pain_points || [],
      strategyAdvice: bf.strategy_advice,
    })),
    painPoints: structured.pain_points.map((p, idx) => ({
      emoji: "😠",
      title: p.title,
      userVoices: p.user_voices,
      dataImpression: p.data_impression || "",
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
    _rawHtml: backendReport.report_html,
  } as ReportData & { _rawHtml?: string | null };
}

// ============================================================================
// Component Implementation
// ============================================================================

const ReportPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<"welcome" | "selector" | "detail">("welcome");
  const [selectedDimension, setSelectedDimension] = useState<DimensionKey | null>(null);
  const [viewedDimensions, setViewedDimensions] = useState<Set<DimensionKey>>(new Set());
  const [showCelebration, setShowCelebration] = useState(false);

  const dimensions = useMemo(() => {
    const counts = {
      battlefields: reportData?.battlefields.length ?? 0,
      painPoints: reportData?.painPoints.length ?? 0,
      drivers: reportData?.drivers.length ?? 0,
      opportunities: reportData?.opportunities.length ?? 0,
    };

    const buildCountDescription = (count: number, withCount: (value: number) => string, emptyState: string) => (
      count > 0 ? withCount(count) : emptyState
    );

    return BASE_DIMENSIONS.map((dim) => {
      switch (dim.key) {
        case "battlefields":
          return {
            ...dim,
            description: buildCountDescription(
              counts.battlefields,
              (value) => `锁定 ${value} 个高潜力社群，了解用户画像、常见痛点与进入策略建议`,
              "数据不足，暂未形成稳定的核心社群画像",
            ),
          };
        case "painPoints":
          return {
            ...dim,
            description: buildCountDescription(
              counts.painPoints,
              (value) => `倾听用户真实声音，发现 ${value} 个最常见且与产品直接相关的核心痛点`,
              "数据不足，暂未形成稳定的核心痛点",
            ),
          };
        case "drivers":
          return {
            ...dim,
            description: buildCountDescription(
              counts.drivers,
              (value) => `掌握用户真正想要的 ${value} 大核心价值，理解购买决策的关键驱动因素`,
              "数据不足，暂未形成稳定的购买驱动力",
            ),
          };
        case "opportunities":
          return {
            ...dim,
            description: buildCountDescription(
              counts.opportunities,
              (value) => `${value} 张清晰的机会卡，结合痛点和驱动力，指明可执行的产品方向`,
              "数据不足，暂未形成明确的商业机会",
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
      setReportData(adaptReportData(reportResponse));
      void getTaskSources(taskId).catch(() => null);
    } catch (err) {
      console.error('Failed to load report', err);
      if (err instanceof Error && err.message === "Missing report_structured") {
        setErrorMessage("报告结构化内容缺失，无法展示价值解读。请重新生成报告或检查 LLM 配置。");
      } else {
        setErrorMessage("报告加载失败，请稍后重试。");
      }
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
      setCurrentView("selector");
    }, 3000);
  };

  const handleSelectDimension = (key: DimensionKey) => {
    setSelectedDimension(key);
    setViewedDimensions((prev) => new Set([...prev, key]));
    setCurrentView("detail");
  };

  const handleNextDimension = () => {
    if (!selectedDimension) return;
    const currentIndex = dimensions.findIndex((d) => d.key === selectedDimension);
    const nextIndex = (currentIndex + 1) % dimensions.length;
    const nextKey = dimensions[nextIndex]?.key;
    if (nextKey) handleSelectDimension(nextKey);
  };

  const handlePrevDimension = () => {
    if (!selectedDimension) return;
    const currentIndex = dimensions.findIndex((d) => d.key === selectedDimension);
    const prevIndex = currentIndex === 0 ? dimensions.length - 1 : currentIndex - 1;
    const prevKey = dimensions[prevIndex]?.key;
    if (prevKey) handleSelectDimension(prevKey);
  };

  const handleLogout = () => {
    logout();
    window.location.reload();
  };

  const getCardIcon = (icon: string) => {
    switch (icon) {
      case "trending": return <TrendingUp className="w-5 h-5" />;
      case "chart": return <BarChart3 className="w-5 h-5" />;
      case "target": return <Target className="w-5 h-5" />;
      case "lightbulb": return <Lightbulb className="w-5 h-5" />;
      default: return <FileText className="w-5 h-5" />;
    }
  };

  if (loading) {
    return <ReportPageSkeleton />;
  }

  if (errorMessage) {
    return (
      <div className="min-h-screen bg-background">
        <header className="border-b border-border bg-card sticky top-0 z-10">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Search className="w-5 h-5 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-bold text-foreground">Reddit 商业信号扫描器</h1>
            </div>
            <button
              onClick={() => navigate(ROUTES.HOME)}
              className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
            >
              返回首页
            </button>
          </div>
        </header>
        <main className="container mx-auto px-4 py-16">
          <div className="max-w-xl mx-auto text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mx-auto">
              <FileWarning className="w-6 h-6 text-muted-foreground" />
            </div>
            <h2 className="text-2xl font-semibold text-foreground">报告暂时无法展示</h2>
            <p className="text-muted-foreground">{errorMessage}</p>
            <button
              onClick={loadReport}
              className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              重新加载
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (!reportData) {
    return <ReportPageSkeleton />;
  }

  const currentDimensionInfo = dimensions.find(d => d.key === selectedDimension);

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <header className="border-b border-border bg-card sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Reddit 商业信号扫描器</h1>
          </div>
          <div className="flex gap-2">
            {isAuthenticated() && (
              <button
                onClick={handleLogout}
                className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
              >
                退出登录
              </button>
            )}
            <button className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3">
              <Share2 className="w-4 h-4 mr-2" />
              分享报告
            </button>
            <button className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3">
              <Download className="w-4 h-4 mr-2" />
              导出 PDF
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <NavigationBreadcrumb currentStep="report" canNavigateBack={false} />

        {/* Celebration Overlay */}
        {showCelebration && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm animate-in fade-in zoom-in duration-300">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center mx-auto animate-bounce">
                <Trophy className="w-10 h-10 text-primary-foreground" />
              </div>
              <h2 className="text-2xl font-bold text-foreground">恭喜完成全部探索！</h2>
              <p className="text-muted-foreground">你已查看所有 5 个维度的洞察</p>
            </div>
          </div>
        )}

        {/* WELCOME VIEW */}
        {currentView === "welcome" && (
          <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-500">
            <div className="text-center space-y-3">
              <div className="flex items-center justify-center gap-2">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary" />
                </div>
              </div>
              <h1 className="text-3xl font-bold text-foreground">市场洞察报告已生成</h1>
              <p className="text-muted-foreground">基于 Reddit 社区讨论数据深度分析</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {reportData.decisionCards.map((card, index) => (
                <div key={index} className="rounded-xl border bg-card text-card-foreground shadow-sm hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30 p-6">
                  <div className="flex gap-4">
                    <div className={clsx("w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0", card.iconBgColor, card.iconColor)}>
                      {getCardIcon(card.icon)}
                    </div>
                    <div className="flex-1 space-y-3">
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-muted-foreground">{card.title}</p>
                        <h3 className="text-lg font-semibold text-foreground leading-snug">{card.conclusion}</h3>
                      </div>
                      <ul className="space-y-2">
                        {card.details.map((detail, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary/50 mt-2 flex-shrink-0" />
                            <span>{detail}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-background to-primary/5 p-12 text-center">
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
              <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
              
              <div className="relative z-10 space-y-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center mx-auto shadow-sm">
                  <LayoutGrid className="w-8 h-8 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-foreground">我们已为你准备了 5 个维度帮助你洞察</h2>
                  <p className="text-muted-foreground max-w-lg mx-auto mt-2">
                    包括市场健康度诊断、核心战场推荐、用户痛点洞察、购买驱动力分析和商业机会
                  </p>
                </div>
                <button
                  onClick={() => setCurrentView("selector")}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-8"
                >
                  继续探索 <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SELECTOR VIEW */}
        {currentView === "selector" && (
          <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-right-4 duration-500">
            {viewedDimensions.size > 0 && (
              <div className="flex items-center justify-between bg-muted/30 rounded-xl p-4">
                <div className="text-sm text-muted-foreground">
                  探索进度：<span className="font-semibold text-foreground">{viewedDimensions.size}</span> / {dimensions.length} 个维度
                </div>
                <div className="flex gap-2">
                  {dimensions.map(dim => (
                    <div 
                      key={dim.key} 
                      className={clsx(
                        "w-3 h-3 rounded-full transition-all",
                        viewedDimensions.has(dim.key) ? "bg-primary scale-110" : "bg-muted-foreground/30"
                      )} 
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold text-foreground">请问你想先探索哪个方面？</h2>
              <p className="text-muted-foreground">选择一个维度开始深入了解</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {dimensions.map((dim) => (
                <button
                  key={dim.key}
                  onClick={() => handleSelectDimension(dim.key)}
                  className={clsx(
                    "group relative text-left p-6 rounded-2xl border-2 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl",
                    dim.bgColor, dim.borderColor, "hover:border-primary"
                  )}
                >
                  {viewedDimensions.has(dim.key) && (
                    <div className="absolute -top-2 -right-2 bg-background rounded-full px-2 py-0.5 border text-xs font-medium shadow flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> 已查看
                    </div>
                  )}
                  <div className="flex items-start gap-4">
                    <div className={clsx("w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform", dim.iconBgColor, dim.color)}>
                      {dim.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-foreground text-lg mb-2 group-hover:text-primary transition-colors">{dim.title}</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">{dim.description}</p>
                    </div>
                  </div>
                  <div className="absolute right-4 bottom-4 opacity-0 group-hover:opacity-100 transition-opacity text-primary">
                    <ArrowRight className="w-5 h-5" />
                  </div>
                </button>
              ))}

              <button
                onClick={() => navigate(ROUTES.HOME)}
                className="group text-left p-6 rounded-2xl border-2 border-dashed border-muted-foreground/30 hover:border-primary/50 transition-all duration-300 hover:bg-muted/30 flex flex-col items-center justify-center min-h-[160px]"
              >
                <div className="w-14 h-14 rounded-xl bg-muted/50 flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                  <Plus className="w-7 h-7 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <h3 className="font-semibold text-muted-foreground group-hover:text-foreground transition-colors">新建分析</h3>
                <p className="text-xs text-muted-foreground mt-1">分析其他产品方向</p>
              </button>

              {/* View Full Report Card */}
              {reportData && (
                <button
                  onClick={() => {
                    const html = (reportData as any)._rawHtml; 
                    if (html) {
                      const newWindow = window.open();
                      if (newWindow) {
                        newWindow.document.write(html);
                        newWindow.document.close();
                      }
                    } else {
                      alert("暂无完整 HTML 报告");
                    }
                  }}
                  className="group text-left p-6 rounded-2xl border-2 border-dashed border-muted-foreground/30 hover:border-primary/50 transition-all duration-300 hover:bg-muted/30 flex flex-col items-center justify-center min-h-[160px]"
                >
                  <div className="w-14 h-14 rounded-xl bg-muted/50 flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                    <FileText className="w-7 h-7 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <h3 className="font-semibold text-muted-foreground group-hover:text-foreground transition-colors">完整报告</h3>
                  <p className="text-xs text-muted-foreground mt-1">查看完整报告</p>
                </button>
              )}
            </div>

            <div className="text-center">
              <button 
                onClick={() => setCurrentView("welcome")}
                className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                返回查看决策卡片
              </button>
            </div>
          </div>
        )}

        {/* DETAIL VIEW */}
        {currentView === "detail" && currentDimensionInfo && (
          <div className="max-w-4xl mx-auto space-y-6 animate-in slide-in-from-right-8 duration-500">
            <div className="flex items-center justify-between">
              <button 
                onClick={() => setCurrentView("selector")}
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
                      "w-2.5 h-2.5 rounded-full",
                      dim.key === selectedDimension ? "bg-primary scale-125" : viewedDimensions.has(dim.key) ? "bg-primary/40" : "bg-muted"
                    )}
                  />
                ))}
              </div>
            </div>

            <div className={clsx("rounded-xl p-6 border-2 flex items-center gap-4", currentDimensionInfo.bgColor, currentDimensionInfo.borderColor)}>
              <div className={clsx("w-14 h-14 rounded-xl flex items-center justify-center", currentDimensionInfo.iconBgColor, currentDimensionInfo.color)}>
                {currentDimensionInfo.icon}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-foreground">{currentDimensionInfo.title}</h2>
                <p className="text-muted-foreground">{currentDimensionInfo.description}</p>
              </div>
            </div>

            {/* Dynamic Content Rendering based on Dimension */}
            {selectedDimension === "marketHealth" && (
              <div className="space-y-6">
                <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                  <h3 className="font-semibold flex items-center gap-2 text-lg"><Activity className="w-5 h-5 text-blue-600"/> 竞争饱和度分析</h3>
                  <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
                    <span className="font-medium">综合判断</span>
                    <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded text-xs font-semibold">{reportData.marketHealth.competitionSaturation.level}</span>
                  </div>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground">依据：</p>
                    {reportData.marketHealth.competitionSaturation.details.map((d, i) => (
                      <div key={i} className="flex gap-2"><span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />{d}</div>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                  <h3 className="font-semibold flex items-center gap-2 text-lg"><BarChart3 className="w-5 h-5 text-primary"/> P/S Ratio</h3>
                  <div className="flex items-center justify-between p-4 bg-primary/5 rounded-lg">
                    <span className="font-medium">比率</span>
                    <span className="text-2xl font-bold text-primary">{reportData.marketHealth.psRatio.ratio}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{reportData.marketHealth.psRatio.interpretation}</p>
                </div>
              </div>
            )}

            {selectedDimension === "battlefields" && (
              <div className="space-y-4">
                {reportData.battlefields.map((bf, i) => (
                  <div key={i} className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                    <div className="flex items-center gap-2">
                      <Users className="w-5 h-5 text-purple-600" />
                      <h3 className="font-bold text-lg">{bf.name}</h3>
                    </div>
                    <div className="flex gap-2">
                      {bf.subreddits.map(s => <span key={s} className="bg-secondary px-2 py-1 rounded text-xs text-secondary-foreground">{s}</span>)}
                    </div>
                    <div className="p-3 bg-muted/50 rounded-lg text-sm">
                      <span className="font-medium block mb-1">画像</span> {bf.profile}
                    </div>
                    <div className="p-3 bg-primary/5 rounded-lg border border-primary/20 text-sm">
                      <span className="font-medium block mb-1 text-primary">策略建议</span> {bf.strategyAdvice}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Placeholder for other dimensions logic (simplified for length, adapt as needed) */}
            {selectedDimension === "painPoints" && (
              <div className="space-y-4">
                {reportData.painPoints.map((p, i) => (
                  <div key={i} className="rounded-xl border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                    <div className="flex items-center gap-2 text-xl font-bold">
                      <span>{p.emoji}</span> {p.title}
                    </div>
                    <div className="space-y-2">
                      {p.userVoices.map((v, idx) => (
                        <div key={idx} className="flex gap-2 p-3 bg-muted/50 rounded-lg text-sm italic text-muted-foreground">
                          <MessageSquare className="w-4 h-4 mt-1 flex-shrink-0 text-primary" /> {v}
                        </div>
                      ))}
                    </div>
                    {p.dataImpression && (
                      <div className="p-3 bg-muted/40 text-sm rounded-lg">
                        <span className="font-medium">数据印象：</span> {p.dataImpression}
                      </div>
                    )}
                    <div className="p-3 bg-blue-50 text-blue-700 text-sm rounded-lg">
                      <span className="font-medium">解读：</span> {p.interpretation}
                    </div>
                    {p.evidence.length > 0 ? (
                      <div className="space-y-2 text-sm">
                        <div className="font-medium text-muted-foreground">证据溯源：</div>
                        <div className="space-y-2">
                          {p.evidence.map((ev, idx) => (
                            ev.url ? (
                              <a
                                key={`${ev.url}-${idx}`}
                                href={ev.url}
                                target="_blank"
                                rel="noreferrer"
                                className="block rounded-lg border border-dashed border-muted-foreground/40 p-3 hover:border-primary/60 hover:bg-muted/30 transition-colors"
                              >
                                <div className="text-xs text-muted-foreground mb-1">
                                  {ev.community ? `社区：${ev.community}` : "社区：未知"}
                                </div>
                                <div className="text-sm text-foreground">{ev.text}</div>
                              </a>
                            ) : (
                              <div key={idx} className="block rounded-lg border border-dashed border-muted-foreground/40 p-3 bg-muted/10">
                                <div className="text-xs text-muted-foreground mb-1">
                                  {ev.community ? `社区：${ev.community}` : "社区：未知"}
                                </div>
                                <div className="text-sm text-foreground">{ev.text}</div>
                                <div className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                                  <AlertTriangle className="w-3 h-3" /> 数据不足，暂无原帖链接
                                </div>
                              </div>
                            )
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 bg-muted/20 text-sm rounded-lg text-muted-foreground italic">
                        暂无证据溯源数据
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {selectedDimension === "drivers" && (
              <div className="space-y-4">
                {reportData.drivers.map((d, i) => (
                  <div key={i} className="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
                    <h3 className="font-bold text-lg flex items-center gap-2 mb-2">
                      <CheckCircle2 className="w-5 h-5 text-green-600" /> {d.title}
                    </h3>
                    <p className="text-muted-foreground">{d.description}</p>
                  </div>
                ))}
              </div>
            )}

            {selectedDimension === "opportunities" && (
              <div className="space-y-4">
                {reportData.opportunities.map((o, i) => (
                  <div key={i} className="rounded-xl border border-amber-200 bg-amber-50/30 p-6 space-y-4">
                    <h3 className="font-bold text-lg flex items-center gap-2 text-amber-800">
                      <Lightbulb className="w-5 h-5" /> {o.title}
                    </h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-muted-foreground block mb-1">定位</span>
                        {o.productPositioning}
                      </div>
                      <div>
                        <span className="font-medium text-muted-foreground block mb-1">卖点</span>
                        <ul className="list-disc pl-4">{o.coreSellingPoints.map((sp, idx) => <li key={idx}>{sp}</li>)}</ul>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center justify-between pt-6 border-t border-border">
              <button 
                onClick={handlePrevDimension}
                className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-9 px-3"
                disabled={dimensions.findIndex(d => d.key === selectedDimension) === 0}
              >
                <ChevronLeft className="w-4 h-4 mr-2" /> 上一个维度
              </button>
              
              {dimensions.findIndex(d => d.key === selectedDimension) === dimensions.length - 1 ? (
                <button 
                  onClick={handleCompleteExploration}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-3"
                >
                  完成探索 <CheckCircle2 className="w-4 h-4 ml-2" />
                </button>
              ) : (
                <button 
                  onClick={handleNextDimension}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-9 px-3"
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
