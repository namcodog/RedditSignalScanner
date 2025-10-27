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
