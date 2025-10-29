/**
 * 质量看板页面
 *
 * 基于 Spec 007 User Story 2 (US2) - Task T030
 * 展示实时质量指标和趋势图
 * 最后更新: 2025-10-27
 */

import React, { useState, useEffect } from 'react';
import { Calendar, TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import MetricsChart from '@/components/MetricsChart';
import { getDailyMetrics } from '@/api/metrics';
import type {
  DailyMetrics,
  ChartDataPoint,
  MetricsQueryParams,
} from '@/types/metrics';
import {
  toChartDataPoint,
  isMetricAbnormal,
  DEFAULT_METRICS_THRESHOLDS,
} from '@/types/metrics';

const DashboardPage: React.FC = () => {
  const [metrics, setMetrics] = useState<DailyMetrics[]>([]);
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<number>(7); // 默认 7 天

  // 加载指标数据
  const loadMetrics = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - dateRange);

      const startDateStr = startDate.toISOString().slice(0, 10);
      const endDateStr = endDate.toISOString().slice(0, 10);

      const query = {
        start_date: startDateStr,
        end_date: endDateStr,
      } satisfies MetricsQueryParams;

      const response = await getDailyMetrics(query);

      setMetrics(response.metrics);
      setChartData(response.metrics.map(toChartDataPoint));
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, [dateRange]);

  // 计算最新指标
  const latestMetric = metrics.length > 0 ? metrics[metrics.length - 1] : null;
  const hasAbnormal = latestMetric ? isMetricAbnormal(latestMetric) : false;

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationBreadcrumb
        items={[
          { label: '首页', path: '/' },
          { label: '质量看板', path: '/dashboard' },
        ]}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-blue-600" />
            质量看板
          </h1>
          <p className="mt-2 text-gray-600">
            实时监控系统质量指标，确保数据健康运行
          </p>
        </div>

        {/* 日期范围选择器 */}
        <div className="mb-6 flex items-center gap-4">
          <Calendar className="w-5 h-5 text-gray-500" />
          <span className="text-sm text-gray-700">日期范围：</span>
          <div className="flex gap-2">
            {[7, 14, 30].map((days) => (
              <button
                key={days}
                onClick={() => setDateRange(days)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  dateRange === days
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                }`}
              >
                最近 {days} 天
              </button>
            ))}
          </div>
          <button
            onClick={loadMetrics}
            disabled={isLoading}
            className="ml-auto px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-red-800">加载失败</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* 最新指标卡片 */}
        {latestMetric && (
          <div className="mb-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="缓存命中率"
              value={`${Math.round(latestMetric.cache_hit_rate * 100)}%`}
              isAbnormal={
                latestMetric.cache_hit_rate * 100 <
                DEFAULT_METRICS_THRESHOLDS.minCacheHitRate
              }
              threshold={`目标 ≥${DEFAULT_METRICS_THRESHOLDS.minCacheHitRate}%`}
            />
            <MetricCard
              title="重复率"
              value={`${Math.round(latestMetric.duplicate_rate * 100)}%`}
              isAbnormal={
                latestMetric.duplicate_rate * 100 >
                DEFAULT_METRICS_THRESHOLDS.maxDuplicateRate
              }
              threshold={`目标 ≤${DEFAULT_METRICS_THRESHOLDS.maxDuplicateRate}%`}
            />
            <MetricCard
              title="Precision@50"
              value={`${Math.round(latestMetric.precision_at_50 * 100)}%`}
              isAbnormal={
                latestMetric.precision_at_50 * 100 <
                DEFAULT_METRICS_THRESHOLDS.minPrecisionAt50
              }
              threshold={`目标 ≥${DEFAULT_METRICS_THRESHOLDS.minPrecisionAt50}%`}
            />
            <MetricCard
              title="有效帖子数"
              value={latestMetric.valid_posts_24h.toLocaleString()}
              isAbnormal={
                latestMetric.valid_posts_24h <
                DEFAULT_METRICS_THRESHOLDS.minValidPosts
              }
              threshold={`目标 ≥${DEFAULT_METRICS_THRESHOLDS.minValidPosts.toLocaleString()}`}
            />
          </div>
        )}

        {/* 异常警告 */}
        {hasAbnormal && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-yellow-800">
                检测到异常指标
              </h3>
              <p className="mt-1 text-sm text-yellow-700">
                部分指标低于安全阈值，请关注系统健康状态
              </p>
            </div>
          </div>
        )}

        {/* 趋势图 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            质量指标趋势
          </h2>
          {isLoading ? (
            <div className="h-96 flex items-center justify-center">
              <div className="text-gray-500">加载中...</div>
            </div>
          ) : (
            <MetricsChart data={chartData} height={400} showLegend={true} />
          )}
        </div>
      </div>
    </div>
  );
};

// 指标卡片组件
interface MetricCardProps {
  title: string;
  value: string;
  isAbnormal: boolean;
  threshold: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  isAbnormal,
  threshold,
}) => {
  return (
    <div
      className={`bg-white rounded-lg shadow-sm border p-4 ${
        isAbnormal ? 'border-red-300 bg-red-50' : 'border-gray-200'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-700">{title}</h3>
        {isAbnormal && (
          <AlertTriangle className="w-4 h-4 text-red-600" />
        )}
      </div>
      <p
        className={`text-2xl font-bold ${
          isAbnormal ? 'text-red-700' : 'text-gray-900'
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-gray-500">{threshold}</p>
    </div>
  );
};

export default DashboardPage;
