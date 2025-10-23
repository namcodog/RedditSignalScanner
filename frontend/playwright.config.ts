/**
 * Playwright 端到端测试配置
 * 
 * 基于 PRD-08 端到端测试规范
 * 最后更新: 2025-10-13 Day 7
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  // E2E 失败快照保存配置
  outputDir: '../reports/failed_e2e',

  use: {
    baseURL: 'http://localhost:3006',
    trace: 'retain-on-failure',  // 失败时保留 trace
    screenshot: 'only-on-failure',  // 失败时截图
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3006',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});

