import { useState, useEffect, useMemo, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Search,
  MessageSquare,
  Users,
  Lightbulb,
  ArrowLeft,
  Download,
  FileJson,
  FileText,
  Loader2,
  AlertCircle,
  ChevronDown,
  TrendingUp,
  Share2,
} from 'lucide-react';

import { getAnalysisReport, submitBetaFeedback } from '@/api/analyze.api';
import type { ReportResponse } from '@/types';
import { ROUTES } from '@/router';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import PainPointsList from '@/components/PainPointsList';
import CompetitorsList from '@/components/CompetitorsList';
import OpportunitiesList from '@/components/OpportunitiesList';
import { EntityHighlights } from '@/components/EntityHighlights';
import { exportToJSON, exportToCSV, exportToText } from '@/utils/export';
import { normalizePainPoints } from '@/lib/report/pain-points';
import { classifyReportError, type ReportErrorState } from '@/utils/report-error';
import { ReportPageSkeleton } from '@/components/SkeletonLoader';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { FeedbackDialog } from '@/components/FeedbackDialog';
import { ActionItemsList } from '@/components/ActionItem';
import { useTranslation } from '@/i18n/TranslationProvider';
import { useToast } from '@/components/ui/toast';
import {
  REPORT_LOADING_STAGES,
  REPORT_EXPORT_STAGES,
  type ProgressStage,
  type ExportStageId,
} from '@/config/report';
import {
  addExportHistoryEntry,
  getExportHistory,
  type ExportHistoryEntry,
} from '@/utils/exportHistory';

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

export interface ReportSectionDefinition {
  id: string;
  labelKey?: string;
  label?: string;
  shouldRender?: (report: ReportResponse) => boolean;
  render: (context: { report: ReportResponse }) => ReactNode;
}

interface ReportPageProps {
  sections?: ReportSectionDefinition[] | undefined;
}

const waitForNextFrame = async () => {
  await new Promise(resolve => {
    setTimeout(resolve, 0);
  });
};

const ReportPage: React.FC<ReportPageProps> = ({ sections }) => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { t, locale, setLocale } = useTranslation();
  const toast = useToast();

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState<ReportErrorState | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'text' | 'pdf' | null>(null);
  const [showExportHistory, setShowExportHistory] = useState(false);
  const [exportHistory, setExportHistory] = useState<ExportHistoryEntry[]>(() => getExportHistory());
  const [loadingStage, setLoadingStage] = useState<ProgressStage>(REPORT_LOADING_STAGES[0]!);
  const [exportStage, setExportStage] = useState<ProgressStage>(REPORT_EXPORT_STAGES[0]!);
  const [isExportProgressVisible, setIsExportProgressVisible] = useState(false);

  const handleLocaleChange = useCallback(
    (next: 'zh' | 'en') => {
      if (next === locale) return;
      setLocale(next);
    },
    [locale, setLocale]
  );

  const resolveLoadingStage = useCallback(
    (id: string): ProgressStage =>
      REPORT_LOADING_STAGES.find(stage => stage.id === id) ?? REPORT_LOADING_STAGES[0]!,
    []
  );

  const resolveExportStage = useCallback(
    (id: ExportStageId): ProgressStage =>
      REPORT_EXPORT_STAGES.find(stage => stage.id === id) ?? REPORT_EXPORT_STAGES[0]!,
    []
  );

  const setLoadingStageById = useCallback(
    (id: string) => {
      setLoadingStage(resolveLoadingStage(id));
    },
    [resolveLoadingStage]
  );

  const setExportStageById = useCallback(
    (id: ExportStageId) => {
      setExportStage(resolveExportStage(id));
    },
    [resolveExportStage]
  );

  const loadReport = useCallback(async () => {
    if (!taskId) {
      return;
    }

    try {
      setLoading(true);
      setErrorState(null);
      setLoadingStageById('cache');
      await waitForNextFrame();
      setLoadingStageById('fetch');
      const data = await getAnalysisReport(taskId);
      setLoadingStageById('hydrate');
      setReport(data);
      setLoadingStageById('render');
    } catch (err) {
      console.error('[ReportPage] Failed to fetch report:', err);
      setErrorState(classifyReportError(err));
    } finally {
      await waitForNextFrame();
      setLoading(false);
    }
  }, [taskId, setLoadingStageById]);

  const handleRetry = useCallback(() => {
    void loadReport();
  }, [loadReport]);


  const handleShare = useCallback(async () => {
    if (!taskId) return;

    const win = typeof window === 'undefined' ? undefined : window;
    const nav = typeof navigator === 'undefined' ? undefined : navigator;
    const doc = typeof document === 'undefined' ? undefined : document;
    const shareUrl = `${win?.location.origin ?? ''}/report/${taskId}`;

    try {
      if (nav?.share) {
        await nav.share({
          title: t('report.title'),
          text: t('report.share.description'),
          url: shareUrl,
        });
        toast.success(t('report.share.success'));
        return;
      }

      if (nav?.clipboard?.writeText) {
        await nav.clipboard.writeText(shareUrl);
        toast.success(t('report.share.success'));
        return;
      }

      if (!doc) {
        toast.error(t('report.share.error'));
        return;
      }

      const input = doc.createElement('input');
      input.value = shareUrl;
      doc.body.appendChild(input);
      input.select();
      const copied = typeof doc.execCommand === 'function' && doc.execCommand('copy');
      doc.body.removeChild(input);
      if (copied) {
        toast.success(t('report.share.success'));
      } else {
        toast.error(t('report.share.error'));
      }
    } catch (err) {
      console.error('[ReportPage] Share failed:', err);
      toast.error(t('report.share.error'));
    }
  }, [taskId, t, toast]);



  useEffect(() => {
    if (!taskId) {
      navigate(ROUTES.HOME);
      return;
    }

    void loadReport();
  }, [taskId, navigate, loadReport]);

  const handleExport = useCallback(
    async (format: 'json' | 'csv' | 'text' | 'pdf') => {
      if (!report || !taskId) return;

      setExporting(true);
      setExportFormat(format);
      setIsExportProgressVisible(true);
      setExportStageById('prepare');
      setShowExportMenu(false);

      try {
        await waitForNextFrame();
        setExportStageById('format');

        // PDF 格式通过后端 API 下载
        if (format === 'pdf') {
          const token = localStorage.getItem('token');
          if (!token) {
            throw new Error('未登录');
          }

          const url = `/api/report/${taskId}/download?format=pdf`;
          const response = await fetch(url, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            throw new Error(`下载失败: ${response.statusText}`);
          }

          const blob = await response.blob();
          const downloadUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = `reddit-signal-scanner-${taskId}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(downloadUrl);
        } else {
          // 其他格式使用客户端导出
          switch (format) {
            case 'json':
              exportToJSON(report.report, taskId);
              break;
            case 'csv':
              exportToCSV(report.report, taskId);
              break;
            case 'text':
              exportToText(report.report, taskId);
              break;
          }
        }

        setExportStageById('history');
        const updatedHistory = addExportHistoryEntry({
          taskId,
          format,
          timestamp: new Date().toISOString(),
        });
        setExportHistory(updatedHistory);
        await waitForNextFrame();
        setExportStageById('complete');
      } catch (err) {
        console.error('[ReportPage] Export failed:', err);
        alert(t('report.export.error'));
      } finally {
        await waitForNextFrame();
        setIsExportProgressVisible(false);
        setExporting(false);
        setExportFormat(null);
        setExportStageById('prepare');
      }
    },
    [report, taskId, t, setExportStageById]
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (showExportMenu && !target.closest('.export-menu-container')) {
        setShowExportMenu(false);
      }
      if (showExportHistory && !target.closest('.export-history-container')) {
        setShowExportHistory(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExportMenu, showExportHistory]);

  const totalOpportunities = report?.report?.opportunities?.length ?? 0;
  const totalCommunities = report?.report?.executive_summary?.total_communities ?? 0;

  const formatHistoryTimestamp = useCallback(
    (iso: string) => {
      try {
        const date = new Date(iso);
        return date.toLocaleString(locale === 'en' ? 'en-US' : 'zh-CN');
      } catch {
        return iso;
      }
    },
    [locale]
  );

  const formatExportLabel = useCallback(
    (format: 'json' | 'csv' | 'text' | 'pdf') => {
      switch (format) {
        case 'json':
          return t('report.export.format.json');
        case 'csv':
          return t('report.export.format.csv');
        case 'text':
          return t('report.export.format.text');
        case 'pdf':
          return t('report.export.options.pdf');
      }
    },
    [t]
  );

  const defaultSections = useMemo(() => buildDefaultSections(t), [t]);

  const combinedSections = useMemo(() => {
    if (!report) {
      return sections ?? [];
    }
    const extras = sections ?? [];
    const merged = [...defaultSections, ...extras];
    return merged.filter(section =>
      section.shouldRender ? section.shouldRender(report) : true
    );
  }, [defaultSections, sections, report]);

  if (loading) {
    return (
      <div className="relative">
        <ReportPageSkeleton />
        <div className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center">
          <div
            data-testid="report-loading-progress"
            role="status"
            aria-live="polite"
            aria-busy="true"
            className="flex items-center gap-3 rounded-full border border-border bg-card px-4 py-2 shadow-lg"
          >
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <div className="flex flex-col gap-1 text-sm text-foreground">
              <span>{t(loadingStage.labelKey)}</span>
              <div className="h-1 w-40 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${loadingStage.progress}%` }}
                  aria-hidden="true"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (errorState || !report) {
    return (
      <div className="app-shell">
        <header className="border-b border-border bg-card">
          <div className="container flex items-center justify-between py-4">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
                <Search className="h-5 w-5" aria-hidden />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-foreground">{t('report.brandName')}</h1>
                <p className="text-xs text-muted-foreground">{t('report.error.subtitle')}</p>
              </div>
            </div>
          </div>
        </header>

        <main className="container flex min-h-[60vh] flex-1 items-center justify-center px-4 py-10">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <h2 className="mb-2 text-2xl font-bold text-destructive">{t('report.error.title')}</h2>
            <p className="mb-6 text-muted-foreground">
              {errorState?.message ?? t('report.error.detail')}
              {errorState?.action ? (
                <span className="mt-2 block text-sm">{errorState.action}</span>
              ) : null}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {errorState?.retryable ? (
                <button
                  onClick={handleRetry}
                  className="inline-flex items-center justify-center rounded-md bg-secondary px-6 py-2 text-sm font-semibold text-secondary-foreground shadow-sm transition hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  重试加载
                </button>
              ) : null}
              <button
                onClick={() => navigate(ROUTES.HOME)}
                className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('report.error.backHome')}
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const initialTab = combinedSections[0]?.id ?? 'overview';

  return (
    <div className="app-shell">
      <header className="border-b border-border bg-card">
        <div className="container flex flex-wrap items-center justify-between gap-4 py-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
              <Search className="h-5 w-5" aria-hidden />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">{t('report.brandName')}</h1>
              <p className="text-xs text-muted-foreground">{t('report.brandTagline')}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center overflow-hidden rounded-md border border-border bg-background text-sm">
              <button
                type="button"
                onClick={() => handleLocaleChange('zh')}
                className={`px-3 py-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  locale === 'zh'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted'
                }`}
              >
                {t('report.locale.zh')}
              </button>
              <button
                type="button"
                onClick={() => handleLocaleChange('en')}
                className={`px-3 py-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  locale === 'en'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted'
                }`}
              >
                {t('report.locale.en')}
              </button>
            </div>
            <button className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              {t('report.nav.login')}
            </button>
            <button className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              {t('report.nav.register')}
            </button>
          </div>
        </div>
      </header>

      <main className="container flex-1 px-4 py-10">
        <div className="mx-auto max-w-6xl space-y-8">
          <NavigationBreadcrumb currentStep="report" canNavigateBack />

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold text-foreground">{t('report.title')}</h2>
              <p className="text-muted-foreground">
                {t('report.subtitle', {
                  count: report.stats?.total_mentions?.toLocaleString() ?? 0,
                })}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => navigate(`/insights/${taskId}`)}
                className="inline-flex items-center justify-center rounded-md bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground transition hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Lightbulb className="mr-2 h-4 w-4" />
                {t('report.viewInsights')}
              </button>

              <button
                onClick={handleShare}
                className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Share2 className="mr-2 h-4 w-4" />
                {t('report.share.button')}
              </button>

              <div className="relative export-menu-container">
                <button
                  onClick={() => setShowExportMenu(prev => !prev)}
                  disabled={exporting}
                  className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {exporting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t('report.export.loading')}
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      {t('report.export.download')}
                      <ChevronDown className="ml-2 h-4 w-4" />
                    </>
                  )}
                </button>

                {showExportMenu && !exporting && (
                  <div className="absolute right-0 z-10 mt-2 w-52 rounded-md border border-border bg-card shadow-lg">
                    <div className="py-1">
                      <button
                        onClick={() => handleExport('json')}
                        role="menuitem"
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileJson className="mr-2 h-4 w-4" />
                        {t('report.export.options.json')}
                      </button>
                      <button
                        onClick={() => handleExport('csv')}
                        role="menuitem"
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        {t('report.export.options.csv')}
                      </button>
                      <button
                        onClick={() => handleExport('text')}
                        role="menuitem"
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        {t('report.export.options.text')}
                      </button>
                      <button
                        onClick={() => handleExport('pdf')}
                        role="menuitem"
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        {t('report.export.options.pdf')}
                      </button>
                    </div>
                  </div>
                )}

                {isExportProgressVisible && exportFormat && (
                  <div className="absolute right-0 top-full z-10 mt-2 rounded-md border border-border bg-card px-4 py-3 text-sm text-foreground shadow-lg dark:border-muted">
                    <div
                      data-testid="report-export-progress"
                      role="progressbar"
                      aria-valuenow={exportStage.progress}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={t('report.export.download')}
                      className="flex flex-col gap-2"
                    >
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        <span>
                          {t(exportStage.labelKey, {
                            format: exportFormat.toUpperCase(),
                          })}
                        </span>
                      </div>
                      <div className="h-1.5 w-48 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${exportStage.progress}%` }}
                          aria-hidden="true"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="relative export-history-container">
                <button
                  onClick={() => setShowExportHistory(prev => !prev)}
                  className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {t('report.export.history')}
                </button>
                {showExportHistory && (
                  <div className="absolute right-0 z-20 mt-2 w-72 max-w-full rounded-md border border-border bg-card shadow-lg">
                    {exportHistory.length === 0 ? (
                      <p className="px-4 py-3 text-sm text-muted-foreground">
                        {t('report.export.history.empty')}
                      </p>
                    ) : (
                      <ul className="max-h-64 overflow-y-auto py-2">
                        {exportHistory.map(entry => (
                          <li key={`${entry.timestamp}-${entry.format}`} className="px-4 py-2 text-sm">
                            <div className="flex items-center justify-between text-foreground">
                              <span className="font-medium">{formatExportLabel(entry.format)}</span>
                              <span className="text-xs text-muted-foreground">
                                {formatHistoryTimestamp(entry.timestamp)}
                              </span>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {t('report.export.history.task', { taskId: entry.taskId })}
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <button
                onClick={() => setShowFeedbackDialog(true)}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('report.actions.startNew')}
              </button>
            </div>
          </div>

          {report.product_description && (
            <div className="rounded-lg border border-border bg-muted/50 p-4">
              <p className="mb-1 text-sm font-medium text-muted-foreground">{t('report.productAnalyzed')}</p>
              <p className="text-sm text-foreground">{report.product_description}</p>
            </div>
          )}

          <ReportSummaryCard report={report} t={t} />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/10">
                <MessageSquare className="h-4 w-4 text-secondary" />
              </div>
              <div className="text-2xl font-bold text-foreground">
                {report.stats?.total_mentions?.toLocaleString() ?? 0}
              </div>
              <p className="text-sm text-muted-foreground">{t('report.metrics.totalMentions')}</p>
            </div>

            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-green-100">
                <TrendingUp className="h-4 w-4 text-green-600" />
              </div>
              <div className="text-2xl font-bold text-foreground">
                {report.overview?.sentiment?.positive ?? 0}%
              </div>
              <p className="text-sm text-muted-foreground">{t('report.metrics.positive')}</p>
            </div>

            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/10">
                <Users className="h-4 w-4 text-secondary" />
              </div>
              <div className="text-2xl font-bold text-foreground">{totalCommunities}</div>
              <p className="text-sm text-muted-foreground">{t('report.metrics.communities')}</p>
            </div>

            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100">
                <Lightbulb className="h-4 w-4 text-amber-600" />
              </div>
              <div className="text-2xl font-bold text-foreground">{totalOpportunities}</div>
              <p className="text-sm text-muted-foreground">{t('report.metrics.opportunities')}</p>
            </div>
          </div>

          {combinedSections.length > 0 && (
            <Tabs key={initialTab} defaultValue={initialTab} className="w-full">
              <TabsList>
                {combinedSections.map(section => (
                  <TabsTrigger key={section.id} value={section.id}>
                    {section.label ?? (section.labelKey ? t(section.labelKey) : section.id)}
                  </TabsTrigger>
                ))}
              </TabsList>

              {combinedSections.map(section => (
                <TabsContent key={section.id} value={section.id} className="space-y-6">
                  {section.render({ report })}
                </TabsContent>
              ))}
            </Tabs>
          )}

          <ReportMetadataCard report={report} t={t} />
        </div>
      </main>

      <FeedbackDialog
        isOpen={showFeedbackDialog}
        onClose={() => setShowFeedbackDialog(false)}
        onSubmit={async rating => {
          if (!taskId) return;

          try {
            const satisfactionMap = {
              helpful: 5,
              neutral: 3,
              'not-helpful': 1,
            } as const;

            await submitBetaFeedback({
              task_id: taskId,
              satisfaction: satisfactionMap[rating],
              missing_communities: [],
              comments: '',
            });
          } catch (err) {
            console.error('[ReportPage] submit feedback failed:', err);
          } finally {
            navigate(ROUTES.HOME);
          }
        }}
      />
    </div>
  );
};

const buildDefaultSections = (t: TranslateFn): ReportSectionDefinition[] => [
  {
    id: 'overview',
    labelKey: 'report.tabs.overview',
    render: ({ report }) => <OverviewSection report={report} t={t} />,
  },
  {
    id: 'pain-points',
    labelKey: 'report.tabs.painPoints',
    render: ({ report }) => <PainPointsSection report={report} t={t} />,
  },
  {
    id: 'competitors',
    labelKey: 'report.tabs.competitors',
    render: ({ report }) => <CompetitorsSection report={report} t={t} />,
  },
  {
    id: 'opportunities',
    labelKey: 'report.tabs.opportunities',
    render: ({ report }) => <OpportunitiesSection report={report} t={t} />,
  },
  {
    id: 'entities',
    labelKey: 'report.tabs.entities',
    render: ({ report }) => <EntitySummarySection report={report} t={t} />,
  },
  {
    id: 'actions',
    labelKey: 'report.tabs.actions',
    render: ({ report }) => <ActionItemsSection report={report} t={t} />,
  },
];

interface SectionProps {
  report: ReportResponse;
  t: TranslateFn;
}

const OverviewSection = ({ report, t }: SectionProps) => (
  <div className="space-y-6">
    {report.overview?.sentiment && (
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="mb-6 text-lg font-semibold text-foreground">{t('report.overview.marketSentiment')}</h3>
        <div className="space-y-4">
          <SentimentBar
            label={t('report.overview.sentiment.positive')}
            value={report.overview.sentiment.positive}
            colorClass="bg-primary"
          />
          <SentimentBar
            label={t('report.overview.sentiment.negative')}
            value={report.overview.sentiment.negative}
            colorClass="bg-red-500"
          />
          <SentimentBar
            label={t('report.overview.sentiment.neutral')}
            value={report.overview.sentiment.neutral}
            colorClass="bg-gray-400"
          />
        </div>
      </div>
    )}

    <div className="rounded-lg border border-border bg-card p-6">
      <h3 className="mb-6 text-lg font-semibold text-foreground">{t('report.overview.topCommunities')}</h3>
      {report.overview?.top_communities && report.overview.top_communities.length > 0 ? (
        <div className="space-y-6">
          {report.overview.top_communities.map((community, index) => (
            <div key={`${community.name}-${index}`} className="flex items-start justify-between gap-4">
              <div>
                <h4 className="text-base font-semibold text-foreground">{community.name}</h4>
                <p className="mt-1 text-sm text-muted-foreground">
                  {t('report.overview.mentions', {
                    count: community.mentions?.toLocaleString() ?? 0,
                  })}
                </p>
              </div>
              <span className="inline-flex items-center rounded-md bg-secondary px-2.5 py-0.5 text-sm font-semibold text-white">
                {t('report.overview.relevance', { score: community.relevance ?? 0 })}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">{t('report.overview.noCommunities')}</p>
        </div>
      )}
    </div>
  </div>
);

const PainPointsSection = ({ report, t }: SectionProps) => {
  const painPoints = report.report.pain_points ?? [];
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {painPoints.length > 0 ? (
        <PainPointsList painPoints={normalizePainPoints(painPoints)} />
      ) : (
        <p className="text-center text-muted-foreground">{t('report.painPoints.empty')}</p>
      )}
    </div>
  );
};

const CompetitorsSection = ({ report, t }: SectionProps) => (
  <div className="rounded-lg border border-border bg-card p-6">
    {report.report.competitors && report.report.competitors.length > 0 ? (
      <CompetitorsList competitors={report.report.competitors} />
    ) : (
      <p className="text-center text-muted-foreground">{t('report.competitors.empty')}</p>
    )}
  </div>
);

const OpportunitiesSection = ({ report, t }: SectionProps) => (
  <div className="rounded-lg border border-border bg-card p-6">
    {report.report.opportunities && report.report.opportunities.length > 0 ? (
      <OpportunitiesList opportunities={report.report.opportunities} />
    ) : (
      <p className="text-center text-muted-foreground">{t('report.opportunities.empty')}</p>
    )}
  </div>
);

const EntitySummarySection = ({ report, t }: SectionProps) => {
  const summary = report.report.entity_summary ?? {
    brands: [],
    features: [],
    pain_points: [],
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h4 className="mb-4 text-sm font-semibold text-foreground">
        {t('report.tabs.entities')}
      </h4>
      <EntityHighlights summary={summary} />
    </div>
  );
};

const ActionItemsSection = ({ report, t }: SectionProps) => (
  <div className="rounded-lg border border-border bg-card p-6">
    {report.report.action_items && report.report.action_items.length > 0 ? (
      <ActionItemsList items={report.report.action_items} />
    ) : (
      <p className="text-center text-muted-foreground">{t('report.actions.empty')}</p>
    )}
  </div>
);

const SentimentBar = ({
  label,
  value,
  colorClass,
}: {
  label: string;
  value: number;
  colorClass: string;
}) => (
  <div className="space-y-2">
    <div className="flex justify-between text-sm">
      <span className="font-medium text-foreground">{label}</span>
      <span className="font-medium text-muted-foreground">{value}%</span>
    </div>
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
      <div className={`${colorClass} h-full transition-all`} style={{ width: `${value}%` }} />
    </div>
  </div>
);

const ReportSummaryCard = ({ report, t }: SectionProps) => {
  const summary = report.report.executive_summary;
  if (!summary) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold text-foreground">{t('report.summary.title')}</h3>
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryItem
          label={t('report.summary.totalCommunities')}
          value={summary.total_communities?.toLocaleString() ?? '0'}
        />
        <SummaryItem
          label={t('report.summary.keyInsights')}
          value={summary.key_insights?.toLocaleString() ?? '0'}
        />
        <SummaryItem
          label={t('report.summary.topOpportunity')}
          value={summary.top_opportunity || t('report.summary.noOpportunity')}
          isText
        />
      </div>
    </div>
  );
};

const SummaryItem = ({
  label,
  value,
  isText = false,
}: {
  label: string;
  value: string;
  isText?: boolean;
}) => (
  <div className="rounded-md border border-border bg-muted/40 p-4">
    <p className="text-sm text-muted-foreground">{label}</p>
    <p className={`mt-2 text-lg font-semibold text-foreground ${isText ? 'break-words' : ''}`}>{value}</p>
  </div>
);

const ReportMetadataCard = ({ report, t }: SectionProps) => (
  <div className="rounded-lg border border-border bg-card p-6">
    <h3 className="mb-4 text-lg font-semibold text-foreground">{t('report.metadata.title')}</h3>
    <div className="grid gap-4 sm:grid-cols-4">
      <MetadataItem
        label={t('report.metadata.analysisVersion')}
        value={report.metadata?.analysis_version ?? '--'}
      />
      <MetadataItem
        label={t('report.metadata.confidence')}
        value={`${Math.round((report.metadata?.confidence_score ?? 0) * 100)}%`}
      />
      <MetadataItem
        label={t('report.metadata.processingTime')}
        value={`${(report.metadata?.processing_time_seconds ?? 0).toFixed(1)}s`}
      />
      <MetadataItem
        label={t('report.metadata.cacheHitRate')}
        value={`${Math.round((report.metadata?.cache_hit_rate ?? 0) * 100)}%`}
      />
    </div>
  </div>
);

const MetadataItem = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-md border border-border bg-muted/40 p-4">
    <p className="text-sm text-muted-foreground">{label}</p>
    <p className="mt-2 text-lg font-semibold text-foreground">{value}</p>
  </div>
);

export default ReportPage;
