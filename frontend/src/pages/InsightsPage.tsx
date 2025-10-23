/**
 * 洞察页面（Insights Page）
 *
 * 洞察卡片 v0：展示洞察卡片列表和证据链
 * 最后更新: 2025-10-22
 *
 * 功能：
 * - 展示洞察卡片列表
 * - 支持按置信度过滤
 * - 支持按子版块过滤
 * - 展示证据面板（带分页）
 * - 返回报告页面
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Filter,
  X,
} from 'lucide-react';
import { insightsService } from '@/services/insights.service';
import type { InsightCard as InsightCardType, Evidence } from '@/types';
import { ROUTES } from '@/router';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import InsightCard from '@/components/InsightCard';
import EvidencePanel from '@/components/EvidencePanel';

const InsightsPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [insights, setInsights] = useState<InsightCardType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 过滤器状态
  const [minConfidence, setMinConfidence] = useState<number>(0.0);
  const [selectedSubreddit, setSelectedSubreddit] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);
  
  // 选中的洞察卡片（用于显示证据面板）
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null);

  // 从 URL 参数读取初始过滤器
  useEffect(() => {
    const minConf = searchParams.get('min_confidence');
    const subreddit = searchParams.get('subreddit');
    
    if (minConf) {
      setMinConfidence(parseFloat(minConf));
    }
    if (subreddit) {
      setSelectedSubreddit(subreddit);
    }
  }, [searchParams]);

  // 获取洞察卡片数据
  useEffect(() => {
    if (!taskId) {
      navigate(ROUTES.HOME);
      return;
    }

    const fetchInsights = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const params: any = {
          task_id: taskId,
        };
        
        if (minConfidence > 0) {
          params.min_confidence = minConfidence;
        }
        
        if (selectedSubreddit) {
          params.subreddit = selectedSubreddit;
        }
        
        const data = await insightsService.getInsights(params);
        setInsights(data.items);
      } catch (err) {
        console.error('[InsightsPage] Failed to fetch insights:', err);
        setError('获取洞察卡片失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    };

    void fetchInsights();
  }, [taskId, navigate, minConfidence, selectedSubreddit]);

  // 应用过滤器
  const handleApplyFilters = () => {
    const params: any = {};
    
    if (minConfidence > 0) {
      params.min_confidence = minConfidence.toString();
    }
    
    if (selectedSubreddit) {
      params.subreddit = selectedSubreddit;
    }
    
    setSearchParams(params);
    setShowFilters(false);
  };

  // 重置过滤器
  const handleResetFilters = () => {
    setMinConfidence(0.0);
    setSelectedSubreddit('');
    setSearchParams({});
    setShowFilters(false);
  };

  // 获取所有唯一的子版块
  const allSubreddits = Array.from(
    new Set(insights.flatMap((insight) => insight.subreddits))
  ).sort();

  // 获取选中洞察卡片的所有证据
  const selectedInsight = insights.find((i) => i.id === selectedInsightId);
  const allEvidences: Evidence[] = selectedInsight?.evidences || [];

  // 加载状态
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">加载洞察卡片中...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <p className="text-lg font-semibold text-foreground">{error}</p>
          <button
            onClick={() => navigate(`/report/${taskId || ''}`)}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <ArrowLeft className="h-4 w-4" />
            返回报告页面
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* 导航面包屑 */}
      <NavigationBreadcrumb
        currentStep="report"
        canNavigateBack={true}
      />

      {/* 主容器 */}
      <div className="container mx-auto px-4 py-8">
        {/* 页面标题 + 过滤器按钮 */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">洞察卡片</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              共 {insights.length} 个洞察
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* 过滤器按钮 */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            >
              <Filter className="h-4 w-4" />
              过滤器
              {(minConfidence > 0 || selectedSubreddit) && (
                <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-secondary text-xs text-secondary-foreground">
                  {(minConfidence > 0 ? 1 : 0) + (selectedSubreddit ? 1 : 0)}
                </span>
              )}
            </button>

            {/* 返回按钮 */}
            <button
              onClick={() => navigate(`/report/${taskId || ''}`)}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <ArrowLeft className="h-4 w-4" />
              返回报告
            </button>
          </div>
        </div>

        {/* 过滤器面板 */}
        {showFilters && (
          <div className="mb-6 rounded-lg border border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">过滤选项</h3>
              <button
                onClick={() => setShowFilters(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {/* 最小置信度 */}
              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">
                  最小置信度: {(minConfidence * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              {/* 子版块过滤 */}
              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">
                  子版块
                </label>
                <select
                  value={selectedSubreddit}
                  onChange={(e) => setSelectedSubreddit(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  <option value="">全部</option>
                  {allSubreddits.map((subreddit) => (
                    <option key={subreddit} value={subreddit}>
                      {subreddit}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={handleApplyFilters}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                应用过滤器
              </button>
              <button
                onClick={handleResetFilters}
                className="rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
              >
                重置
              </button>
            </div>
          </div>
        )}

        {/* 洞察卡片列表 */}
        {insights.length === 0 ? (
          <div className="rounded-lg border border-border bg-card p-12 text-center">
            <p className="text-sm text-muted-foreground">暂无洞察卡片数据</p>
          </div>
        ) : (
          <div className="space-y-6">
            {insights.map((insight) => (
              <InsightCard
                key={insight.id}
                insight={insight}
                defaultExpanded={insight.id === selectedInsightId}
                onToggleEvidence={(id, expanded) => {
                  setSelectedInsightId(expanded ? id : null);
                }}
              />
            ))}
          </div>
        )}

        {/* 证据面板（当选中洞察卡片时显示） */}
        {selectedInsight && allEvidences.length > 0 && (
          <div className="mt-8">
            <h2 className="mb-4 text-2xl font-bold text-foreground">
              证据详情：{selectedInsight.title}
            </h2>
            <EvidencePanel evidences={allEvidences} pageSize={10} />
          </div>
        )}
      </div>
    </div>
  );
};

export default InsightsPage;

