/**
 * 应用入口文件
 * 
 * 最后更新: 2025-10-10 Day 1
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/index.css';
import { TranslationProvider } from '@/i18n/TranslationProvider';
import { ToastProvider } from '@/components/ui/toast';

console.log('[main.tsx] Starting application');

/**
 * 迁移旧的 localStorage token key
 * 从 'token' 迁移到 'auth_token'
 */
const migrateTokenKey = (): void => {
  const oldToken = localStorage.getItem('token');
  const newToken = localStorage.getItem('auth_token');

  // 如果存在旧 token 但没有新 token，则迁移
  if (oldToken && !newToken) {
    console.log('[main.tsx] Migrating token from "token" to "auth_token"');
    localStorage.setItem('auth_token', oldToken);
    localStorage.removeItem('token');
  }
};

// 执行迁移
migrateTokenKey();

const rootElement = document.getElementById('root');

if (rootElement === null) {
  console.error('[main.tsx] Root element not found!');
  throw new Error('Root element not found');
}

console.log('[main.tsx] Root element found, rendering App');

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ToastProvider>
      <TranslationProvider>
        <App />
      </TranslationProvider>
    </ToastProvider>
  </React.StrictMode>
);

console.log('[main.tsx] App rendered');
