/**
 * 骨架屏加载组件
 * 
 * Day 9 UI优化任务
 * 用于 ReportPage 加载状态，提供更好的用户体验
 */

import React from 'react';

/**
 * 骨架屏卡片组件
 */
const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`rounded-lg border border-border bg-card p-6 ${className}`}>
    <div className="space-y-3">
      <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
      <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
      <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
    </div>
  </div>
);

/**
 * 骨架屏指标卡片
 */
const SkeletonMetricCard: React.FC = () => (
  <div className="rounded-lg border border-border bg-card p-4 text-center">
    <div className="mx-auto mb-2 h-8 w-8 animate-pulse rounded-lg bg-muted" />
    <div className="mx-auto mb-2 h-8 w-16 animate-pulse rounded bg-muted" />
    <div className="mx-auto h-4 w-20 animate-pulse rounded bg-muted" />
  </div>
);

/**
 * 骨架屏列表项
 */
const SkeletonListItem: React.FC = () => (
  <div className="rounded-xl border border-border bg-card p-6">
    <div className="flex items-start gap-4">
      <div className="h-8 w-8 shrink-0 animate-pulse rounded-lg bg-muted" />
      <div className="flex-1 space-y-3">
        <div className="h-5 w-full animate-pulse rounded bg-muted" />
        <div className="h-5 w-4/5 animate-pulse rounded bg-muted" />
        <div className="flex gap-2">
          <div className="h-6 w-20 animate-pulse rounded-md bg-muted" />
          <div className="h-6 w-20 animate-pulse rounded-md bg-muted" />
          <div className="h-6 w-20 animate-pulse rounded-md bg-muted" />
        </div>
      </div>
      <div className="shrink-0 text-right">
        <div className="mb-1 h-10 w-12 animate-pulse rounded bg-muted" />
        <div className="h-4 w-16 animate-pulse rounded bg-muted" />
      </div>
    </div>
  </div>
);

/**
 * 完整的报告页面骨架屏
 */
export const ReportPageSkeleton: React.FC = () => {
  return (
    <div className="app-shell">
      {/* Header Skeleton */}
      <header className="border-b border-border bg-card">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 animate-pulse rounded-lg bg-muted" />
            <div className="space-y-2">
              <div className="h-5 w-48 animate-pulse rounded bg-muted" />
              <div className="h-3 w-32 animate-pulse rounded bg-muted" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Skeleton */}
      <main className="container flex-1 px-4 py-10">
        <div className="mx-auto max-w-6xl space-y-8">
          {/* Breadcrumb Skeleton */}
          <div className="flex items-center gap-2">
            <div className="h-4 w-16 animate-pulse rounded bg-muted" />
            <div className="h-4 w-4 animate-pulse rounded bg-muted" />
            <div className="h-4 w-16 animate-pulse rounded bg-muted" />
            <div className="h-4 w-4 animate-pulse rounded bg-muted" />
            <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          </div>

          {/* Header Skeleton */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-9 w-64 animate-pulse rounded bg-muted" />
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-10 w-32 animate-pulse rounded-md bg-muted" />
              <div className="h-10 w-32 animate-pulse rounded-md bg-muted" />
            </div>
          </div>

          {/* Executive Summary Skeleton */}
          <SkeletonCard />

          {/* Metrics Grid Skeleton */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <SkeletonMetricCard />
            <SkeletonMetricCard />
            <SkeletonMetricCard />
            <SkeletonMetricCard />
          </div>

          {/* Pain Points Section Skeleton */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 animate-pulse rounded-xl bg-muted" />
              <div className="space-y-2">
                <div className="h-7 w-32 animate-pulse rounded bg-muted" />
                <div className="h-4 w-40 animate-pulse rounded bg-muted" />
              </div>
            </div>
            <div className="space-y-4">
              <SkeletonListItem />
              <SkeletonListItem />
              <SkeletonListItem />
            </div>
          </div>

          {/* Competitors Section Skeleton */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 animate-pulse rounded-xl bg-muted" />
              <div className="space-y-2">
                <div className="h-7 w-32 animate-pulse rounded bg-muted" />
                <div className="h-4 w-40 animate-pulse rounded bg-muted" />
              </div>
            </div>
            <div className="space-y-4">
              <SkeletonListItem />
              <SkeletonListItem />
            </div>
          </div>

          {/* Opportunities Section Skeleton */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 animate-pulse rounded-xl bg-muted" />
              <div className="space-y-2">
                <div className="h-7 w-32 animate-pulse rounded bg-muted" />
                <div className="h-4 w-40 animate-pulse rounded bg-muted" />
              </div>
            </div>
            <div className="space-y-4">
              <SkeletonListItem />
              <SkeletonListItem />
            </div>
          </div>

          {/* Metadata Skeleton */}
          <SkeletonCard />
        </div>
      </main>
    </div>
  );
};

/**
 * 简单的骨架屏加载器（用于其他页面）
 */
export const SimpleSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
};

export default ReportPageSkeleton;

