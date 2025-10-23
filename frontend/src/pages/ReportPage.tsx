/**
 * 报告页面（Report Page）
 *
 * 基于 PRD-05 前端交互设计 & 最终界面设计效果
 * 最后更新: 2025-10-13 Day 8
 * 状态: 完整实现（Day 8）
 *
 * 功能：
 * - 展示分析报告概览（Day 7）
 * - 痛点、竞品、机会列表（Day 8）✅
 * - 导出功能（Day 8）✅
 * - 返回首页
 */

import { useState, useEffect } from 'react';
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
import { exportToJSON, exportToCSV, exportToText } from '@/utils/export';
import { ReportPageSkeleton } from '@/components/SkeletonLoader';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { FeedbackDialog } from '@/components/FeedbackDialog';
import { ActionItemsList } from '@/components/ActionItem';

const ReportPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'text' | null>(null);

  // 获取报告数据
  useEffect(() => {
    if (!taskId) {
      navigate(ROUTES.HOME);
      return;
    }

    const fetchReport = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getAnalysisReport(taskId);
        setReport(data);
      } catch (err) {
        console.error('[ReportPage] Failed to fetch report:', err);
        setError('获取报告失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    };

    void fetchReport();
  }, [taskId, navigate]);

  // 导出处理函数（带进度指示）
  const handleExport = async (format: 'json' | 'csv' | 'text') => {
    if (!report || !taskId) return;

    setExporting(true);
    setExportFormat(format);
    setShowExportMenu(false);

    try {
      // 模拟导出延迟，让用户看到进度指示
      await new Promise(resolve => setTimeout(resolve, 300));

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

      // 显示成功提示
      console.log(`[ReportPage] ${format.toUpperCase()} 导出成功`);
    } catch (err) {
      console.error('[ReportPage] Export failed:', err);
      alert('导出失败，请稍后重试');
    } finally {
      setExporting(false);
      setExportFormat(null);
    }
  };

  // 点击外部关闭导出菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (showExportMenu && !target.closest('.export-menu-container')) {
        setShowExportMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExportMenu]);

  // 加载状态 - 使用骨架屏
  if (loading) {
    return <ReportPageSkeleton />;
  }

  // 错误状态
  if (error || !report) {
    return (
      <div className="app-shell">
        <header className="border-b border-border bg-card">
          <div className="container flex items-center justify-between py-4">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
                <Search className="h-5 w-5" aria-hidden />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-foreground">
                  Reddit 商业信号扫描器
                </h1>
                <p className="text-xs text-muted-foreground">报告加载失败</p>
              </div>
            </div>
          </div>
        </header>

        <main className="container flex min-h-[60vh] flex-1 items-center justify-center px-4 py-10">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <h2 className="mb-2 text-2xl font-bold text-destructive">
              获取报告失败
            </h2>
            <p className="mb-6 text-muted-foreground">
              {error || '无法加载分析报告，请检查任务ID是否正确或稍后重试'}
            </p>
            <button
              onClick={() => navigate(ROUTES.HOME)}
              className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回首页
            </button>
          </div>
        </main>
      </div>
    );
  }

  // 计算统计数据
  const totalOpportunities = report.report.opportunities?.length || 0;
  const totalCommunities = report.report.executive_summary?.total_communities || 0;

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
              <Search className="h-5 w-5" aria-hidden />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">
                Reddit 商业信号扫描器
              </h1>
              <p className="text-xs text-muted-foreground">市场洞察报告</p>
            </div>
          </div>

          {/* 登录/注册按钮 */}
          <div className="flex items-center space-x-2">
            <button className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              登录
            </button>
            <button className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              注册
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container flex-1 px-4 py-10">
        <div className="mx-auto max-w-6xl space-y-8">
          {/* Navigation Breadcrumb */}
          <NavigationBreadcrumb currentStep="report" canNavigateBack={true} />

          {/* Report Header */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold text-foreground">市场洞察报告</h2>
              <p className="text-muted-foreground">
                分析已完成 • 已分析 {report.stats?.total_mentions?.toLocaleString() || 0} 条提及
              </p>
            </div>
            <div className="flex items-center space-x-2">
              {/* 查看洞察卡片按钮 */}
              <button
                onClick={() => navigate(`/insights/${taskId}`)}
                className="inline-flex items-center justify-center rounded-md bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground transition hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Lightbulb className="mr-2 h-4 w-4" />
                查看洞察卡片
              </button>

              {/* 分享按钮 */}
              <button
                className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Share2 className="mr-2 h-4 w-4" />
                分享
              </button>

              {/* 导出PDF下拉菜单 */}
              <div className="relative export-menu-container">
                <button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  disabled={exporting}
                  className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {exporting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      导出中...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      导出PDF
                      <ChevronDown className="ml-2 h-4 w-4" />
                    </>
                  )}
                </button>

                {showExportMenu && !exporting && (
                  <div className="absolute right-0 z-10 mt-2 w-48 rounded-md border border-border bg-card shadow-lg">
                    <div className="py-1">
                      <button
                        onClick={() => handleExport('json')}
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileJson className="mr-2 h-4 w-4" />
                        导出为 JSON
                      </button>
                      <button
                        onClick={() => handleExport('csv')}
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        导出为 CSV
                      </button>
                      <button
                        onClick={() => handleExport('text')}
                        className="flex w-full items-center px-4 py-2 text-sm text-foreground transition hover:bg-muted"
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        导出为 TXT
                      </button>
                    </div>
                  </div>
                )}

                {/* 导出成功提示 */}
                {exporting && exportFormat && (
                  <div className="absolute right-0 top-full z-10 mt-2 rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800 shadow-sm dark:border-green-900 dark:bg-green-950 dark:text-green-200">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      正在导出 {exportFormat.toUpperCase()}...
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={() => setShowFeedbackDialog(true)}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                开始新分析
              </button>
            </div>
          </div>

          {/* 已分析产品卡片 */}
          {report.product_description && (
            <div className="rounded-lg border border-border bg-muted/50 p-4">
              <p className="mb-2 text-sm font-medium text-muted-foreground">已分析产品</p>
              <p className="text-sm text-foreground">{report.product_description}</p>
            </div>
          )}

          {/* Key Metrics Overview */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/10">
                <MessageSquare className="h-4 w-4 text-secondary" />
              </div>
              <div className="text-2xl font-bold text-foreground">
                {report.stats?.total_mentions?.toLocaleString() || 0}
              </div>
              <p className="text-sm text-muted-foreground">总提及数</p>
            </div>

            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-green-100">
                <TrendingUp className="h-4 w-4 text-green-600" />
              </div>
              <div className="text-2xl font-bold text-foreground">
                {report.overview?.sentiment?.positive || 0}%
              </div>
              <p className="text-sm text-muted-foreground">正面情感</p>
            </div>

            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/10">
                <Users className="h-4 w-4 text-secondary" />
              </div>
              <div className="text-2xl font-bold text-foreground">{totalCommunities}</div>
              <p className="text-sm text-muted-foreground">社区数量</p>
            </div>

            <div className="rounded-lg border border-border bg-card p-4 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100">
                <Lightbulb className="h-4 w-4 text-amber-600" />
              </div>
              <div className="text-2xl font-bold text-foreground">{totalOpportunities}</div>
              <p className="text-sm text-muted-foreground">商业机会</p>
            </div>
          </div>

          {/* Tab Navigation */}
          <Tabs defaultValue="overview" className="w-full">
            <TabsList>
              <TabsTrigger value="overview">
                概览
              </TabsTrigger>
              <TabsTrigger value="pain-points">
                用户痛点
              </TabsTrigger>
              <TabsTrigger value="competitors">
                竞品分析
              </TabsTrigger>
              <TabsTrigger value="opportunities">
                商业机会
              </TabsTrigger>
              <TabsTrigger value="actions">
                行动建议
              </TabsTrigger>
            </TabsList>

            {/* 概览 Tab */}
            <TabsContent value="overview" className="space-y-6">
              {/* 市场情感分析 - 使用进度条显示（与 demo 一致） */}
              {report.overview?.sentiment && (
                <div className="rounded-lg border border-border bg-card p-6">
                  <h3 className="mb-6 text-lg font-semibold text-foreground">市场情感</h3>
                  <div className="space-y-4">
                    {/* 正面 */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-foreground">正面</span>
                        <span className="font-medium text-muted-foreground">
                          {report.overview.sentiment.positive}%
                        </span>
                      </div>
                      <div className="bg-primary/20 relative w-full overflow-hidden rounded-full h-2">
                        <div
                          className="bg-primary h-full transition-all"
                          style={{ width: `${report.overview.sentiment.positive}%` }}
                        />
                      </div>
                    </div>

                    {/* 负面 */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-foreground">负面</span>
                        <span className="font-medium text-muted-foreground">
                          {report.overview.sentiment.negative}%
                        </span>
                      </div>
                      <div className="bg-primary/20 relative w-full overflow-hidden rounded-full h-2">
                        <div
                          className="bg-red-600 h-full transition-all"
                          style={{ width: `${report.overview.sentiment.negative}%` }}
                        />
                      </div>
                    </div>

                    {/* 中性 */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-foreground">中性</span>
                        <span className="font-medium text-muted-foreground">
                          {report.overview.sentiment.neutral}%
                        </span>
                      </div>
                      <div className="bg-primary/20 relative w-full overflow-hidden rounded-full h-2">
                        <div
                          className="bg-gray-400 h-full transition-all"
                          style={{ width: `${report.overview.sentiment.neutral}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 热门社区 - 成员数在下方，相关度有紫色底色 */}
              <div className="rounded-lg border border-border bg-card p-6">
                <h3 className="mb-6 text-lg font-semibold text-foreground">热门社区</h3>
                {report.overview?.top_communities && report.overview.top_communities.length > 0 ? (
                  <div className="space-y-6">
                    {report.overview.top_communities.map((community, index) => (
                      <div key={index} className="flex items-start justify-between">
                        {/* 左侧：社区名称 + 成员数 */}
                        <div>
                          <h4 className="text-base font-semibold text-foreground">{community.name}</h4>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {community.mentions?.toLocaleString() || 0} 次提及
                          </p>
                        </div>
                        {/* 右侧：相关度（紫色底色） */}
                        <span className="inline-flex items-center rounded-md bg-secondary px-2.5 py-0.5 text-sm font-semibold text-white">
                          {community.relevance}% 相关
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center">
                    <p className="text-sm text-muted-foreground">暂无社区数据</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* 用户痛点 Tab */}
            <TabsContent value="pain-points" className="space-y-6">
              {report.report.pain_points && report.report.pain_points.length > 0 ? (
                <PainPointsList painPoints={report.report.pain_points} />
              ) : (
                <div className="rounded-lg border border-border bg-card p-6 text-center">
                  <p className="text-muted-foreground">暂无用户痛点数据</p>
                </div>
              )}
            </TabsContent>

            {/* 竞品分析 Tab */}
            <TabsContent value="competitors" className="space-y-6">
              {report.report.competitors && report.report.competitors.length > 0 ? (
                <CompetitorsList competitors={report.report.competitors} />
              ) : (
                <div className="rounded-lg border border-border bg-card p-6 text-center">
                  <p className="text-muted-foreground">暂无竞品分析数据</p>
                </div>
              )}
            </TabsContent>

            {/* 商业机会 Tab */}
            <TabsContent value="opportunities" className="space-y-6">
              {report.report.opportunities && report.report.opportunities.length > 0 ? (
                <OpportunitiesList opportunities={report.report.opportunities} />
              ) : (
                <div className="rounded-lg border border-border bg-card p-6 text-center">
                  <p className="text-muted-foreground">暂无商业机会数据</p>
                </div>
              )}
            </TabsContent>

            {/* 行动建议 Tab */}
            <TabsContent value="actions" className="space-y-6">
              {report.report.action_items && report.report.action_items.length > 0 ? (
                <ActionItemsList items={report.report.action_items} />
              ) : (
                <div className="rounded-lg border border-border bg-card p-6 text-center">
                  <p className="text-muted-foreground">暂无行动建议</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </main>

      {/* 用户反馈弹框 */}
      <FeedbackDialog
        isOpen={showFeedbackDialog}
        onClose={() => setShowFeedbackDialog(false)}
        onSubmit={async (rating) => {
          if (!taskId) return;

          try {
            // 将前端评分映射到后端的 1-5 分
            const satisfactionMap = {
              'helpful': 5,      // 有价值 -> 5分
              'neutral': 3,      // 一般 -> 3分
              'not-helpful': 1,  // 无价值 -> 1分
            };

            await submitBetaFeedback({
              task_id: taskId,
              satisfaction: satisfactionMap[rating],
              missing_communities: [],
              comments: '',
            });

            console.log('✅ 用户反馈已提交:', rating);
          } catch (error) {
            console.error('❌ 提交反馈失败:', error);
          } finally {
            // 无论成功失败都跳转到首页
            navigate(ROUTES.HOME);
          }
        }}
      />
    </div>
  );
};

export default ReportPage;
