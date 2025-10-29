/**
 * 前端路由配置
 * 
 * 基于 PRD-05 前端交互设计
 * 最后更新: 2025-10-10 Day 2
 * 
 * 路由结构：
 * - / - 输入页面（Input Page）
 * - /progress/:taskId - 等待页面（Progress Page）
 * - /report/:taskId - 报告页面（Report Page）
 * - /login - 登录页面
 * - /register - 注册页面
 */

import React, { Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { isAuthenticated } from '@/api';

// 页面组件（骨架，Day 5 后实现）
const InputPage = React.lazy(() => import('@/pages/InputPage'));
const ProgressPage = React.lazy(() => import('@/pages/ProgressPage'));
const ReportPage = React.lazy(() => import('@/pages/ReportPage'));
const InsightsPage = React.lazy(() => import('@/pages/InsightsPage'));
const LoginPage = React.lazy(() => import('@/pages/LoginPage'));
const RegisterPage = React.lazy(() => import('@/pages/RegisterPage'));
const AdminDashboardPage = React.lazy(() => import('@/pages/AdminDashboardPage'));
const CommunityImportPage = React.lazy(() => import('@/pages/admin/CommunityImport'));
const DashboardPage = React.lazy(() => import('@/pages/DashboardPage'));
const NotFoundPage = React.lazy(() => import('@/pages/NotFoundPage'));

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
 * Suspense 包裹组件
 */
const SuspenseWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Suspense fallback={<LoadingFallback />}>{children}</Suspense>;
};

/**
 * 受保护路由组件
 * 
 * 需要用户登录才能访问
 */
interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  if (!isAuthenticated()) {
    // 未登录，重定向到登录页面
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

/**
 * 公开路由组件
 * 
 * 已登录用户访问时重定向到首页
 */
interface PublicRouteProps {
  children: React.ReactNode;
}

const PublicRoute: React.FC<PublicRouteProps> = ({ children }) => {
  if (isAuthenticated()) {
    // 已登录，重定向到首页
    return <Navigate to="/" replace />;
  }
  
  return <>{children}</>;
};

/**
 * 路由配置
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <SuspenseWrapper>
        <InputPage />
      </SuspenseWrapper>
    ),
  },
  {
    path: '/progress/:taskId',
    element: (
      <SuspenseWrapper>
        <ProtectedRoute>
          <ProgressPage />
        </ProtectedRoute>
      </SuspenseWrapper>
    ),
  },
  {
    path: '/report/:taskId',
    element: (
      <SuspenseWrapper>
        <ProtectedRoute>
          <ReportPage />
        </ProtectedRoute>
      </SuspenseWrapper>
    ),
  },
  {
    path: '/insights/:taskId',
    element: (
      <SuspenseWrapper>
        <ProtectedRoute>
          <InsightsPage />
        </ProtectedRoute>
      </SuspenseWrapper>
    ),
  },
  {
    path: '/login',
    element: (
      <SuspenseWrapper>
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      </SuspenseWrapper>
    ),
  },
  {
    path: '/register',
    element: (
      <SuspenseWrapper>
        <PublicRoute>
          <RegisterPage />
        </PublicRoute>
      </SuspenseWrapper>
    ),
  },
  {
    path: '/admin',
    element: (
      <SuspenseWrapper>
        <AdminDashboardPage />
      </SuspenseWrapper>
    ),
  },
  {
    path: '/admin/communities/import',
    element: (
      <SuspenseWrapper>
        <CommunityImportPage />
      </SuspenseWrapper>
    ),
  },
  {
    path: '/dashboard',
    element: (
      <SuspenseWrapper>
        <DashboardPage />
      </SuspenseWrapper>
    ),
  },
  {
    path: '*',
    element: (
      <SuspenseWrapper>
        <NotFoundPage />
      </SuspenseWrapper>
    ),
  },
]);

/**
 * 路由路径常量
 */
export const ROUTES = {
  HOME: '/',
  PROGRESS: (taskId: string) => `/progress/${taskId}`,
  REPORT: (taskId: string) => `/report/${taskId}`,
  INSIGHTS: (taskId: string) => `/insights/${taskId}`,
  LOGIN: '/login',
  REGISTER: '/register',
  ADMIN: '/admin',
  ADMIN_COMMUNITY_IMPORT: '/admin/communities/import',
  DASHBOARD: '/dashboard',
} as const;
