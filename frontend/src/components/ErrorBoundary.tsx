/**
 * 全局错误边界组件
 *
 * 依据 React 官方最佳实践（https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary）
 * 用于捕获子树渲染错误，防止整个应用崩溃。
 */

import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
}

interface ErrorBoundaryProps {
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: unknown, errorInfo: React.ErrorInfo): void {
    // 记录错误以便后续上报
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  override render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined) {
        return this.props.fallback;
      }
      return (
        <div
          role="alert"
          style={{
            padding: '24px',
            margin: '16px',
            borderRadius: '8px',
            backgroundColor: '#fef2f2',
            color: '#991b1b',
            border: '1px solid #fecaca',
          }}
        >
          <h2 style={{ marginBottom: '8px' }}>出现错误</h2>
          <p>页面渲染时发生了异常，请刷新或稍后重试。</p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
