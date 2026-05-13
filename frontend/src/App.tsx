/**
 * 应用根组件
 *
 * 最后更新: 2025-10-10 Day 4
 * 状态: 路由集成完成，等待 Day 5 开始实现页面
 */

import React, { Suspense } from 'react';
import { Aperture } from 'lucide-react';
import { RouterProvider } from 'react-router-dom';
import router from './router';
import ErrorBoundary from './components/ErrorBoundary';

/**
 * 加载中组件
 */
const LoadingFallback: React.FC = () => {
  return (
    <div className="loading-container px-6 text-center">
      <div className="surface-panel w-full max-w-lg rounded-[28px] px-8 py-10">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl surface-brand-mark text-primary-foreground">
          <Aperture className="h-8 w-8" aria-hidden="true" />
        </div>
        <div className="mt-6 inline-flex items-center gap-3 rounded-full border border-border bg-background/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-primary">
          <span className="loading-spinner h-4 w-4" />
          正在接入情报流
        </div>
        <h1 className="mt-5 text-3xl font-semibold text-foreground">Reddit Signal Scanner</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          正在整理这次判断页、动作链和证据面板，马上进入正式界面。
        </p>
      </div>
    </div>
  );
};

/**
 * 应用根组件
 */
const App: React.FC = () => {
  console.log('[App] Rendering App component');

  return (
    <ErrorBoundary fallback={<LoadingFallback />}>
      <Suspense fallback={<LoadingFallback />}>
        <RouterProvider router={router} />
      </Suspense>
    </ErrorBoundary>
  );
};

export default App;
