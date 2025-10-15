/**
 * 应用根组件
 *
 * 最后更新: 2025-10-10 Day 4
 * 状态: 路由集成完成，等待 Day 5 开始实现页面
 */

import React, { Suspense } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import ErrorBoundary from './components/ErrorBoundary';

/**
 * 加载中组件
 */
const LoadingFallback: React.FC = () => {
  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1rem'
    }}>
      <div style={{
        width: '3rem',
        height: '3rem',
        border: '4px solid #3B82F6',
        borderTopColor: 'transparent',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
      }}></div>
      <p>加载中...</p>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
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
