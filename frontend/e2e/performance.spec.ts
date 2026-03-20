import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

import {
  createAcceptanceTokenForUser,
  findLatestRealReportSample,
  injectAuthToken,
} from './helpers/current-world';

const THRESHOLDS = {
  homeLoadMs: 4000,
  reportLoadMs: 5500,
  firstContentfulPaintMs: 2000,
  interactionDelayMs: 300,
  homeResources: 120,
  reportResources: 130,
  scriptResources: 25,
  styleResources: 10,
  memoryMb: 100,
};

const getPerformanceMetrics = async (page: Page) =>
  page.evaluate(() => {
    const navigation = window.performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    const paints = window.performance.getEntriesByType('paint');
    const fcp = paints.find((entry) => entry.name === 'first-contentful-paint');

    return {
      pageLoadTime: navigation ? navigation.loadEventEnd - navigation.fetchStart : 0,
      firstContentfulPaint: fcp ? fcp.startTime : 0,
      resources: window.performance.getEntriesByType('resource').length,
      scripts: window.performance.getEntriesByType('resource').filter((entry) => entry.name.endsWith('.js')).length,
      styles: window.performance.getEntriesByType('resource').filter((entry) => entry.name.endsWith('.css')).length,
    };
  });

test.describe('前端性能测试 - 当前产品口径', () => {
  let authToken = '';
  let reportTaskId = '';

  test.beforeAll(async () => {
    const reportSample = findLatestRealReportSample();
    authToken = createAcceptanceTokenForUser(reportSample.userId, reportSample.userEmail);
    reportTaskId = reportSample.taskId;
  });

  test('首页加载时间应该在当前预算内', async ({ page }) => {
    const start = Date.now();
    await page.goto('/');
    await page.waitForLoadState('load');

    expect(Date.now() - start).toBeLessThan(THRESHOLDS.homeLoadMs);

    const metrics = await getPerformanceMetrics(page);
    expect(metrics.firstContentfulPaint).toBeLessThan(THRESHOLDS.firstContentfulPaintMs);
  });

  test('真实报告页加载时间应该在当前预算内', async ({ page }) => {
    await injectAuthToken(page, authToken);

    const start = Date.now();
    await page.goto(`/report/${reportTaskId}`);
    await expect(
      page.getByRole('heading', { name: /这次(已经值得继续做|先把方向定下来|先决定追不追)/, level: 2 }),
    ).toBeVisible();

    expect(Date.now() - start).toBeLessThan(THRESHOLDS.reportLoadMs);

    const metrics = await getPerformanceMetrics(page);
    expect(metrics.firstContentfulPaint).toBeLessThan(THRESHOLDS.firstContentfulPaintMs);
  });

  test('输入页打字反馈应该足够快', async ({ page }) => {
    await page.goto('/');
    const textarea = page.getByRole('textbox', { name: '产品描述' });

    const start = Date.now();
    await textarea.fill('一款帮助产品经理管理需求优先级的工具');
    await expect(page.getByText('字数适合分析')).toBeVisible();

    expect(Date.now() - start).toBeLessThan(THRESHOLDS.interactionDelayMs);
  });

  test('报告页从判断卡进入逐维探索应该足够快', async ({ page }) => {
    await injectAuthToken(page, authToken);
    await page.goto(`/report/${reportTaskId}`);

    const start = Date.now();
    await page.getByRole('button', { name: '逐维探索' }).first().click();
    await expect(page.getByRole('heading', { name: '继续拆证据', level: 2 })).toBeVisible();

    expect(Date.now() - start).toBeLessThan(THRESHOLDS.interactionDelayMs * 2);
  });

  test('首页资源数量应该保持在当前合理范围', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const metrics = await getPerformanceMetrics(page);
    expect(metrics.resources).toBeLessThan(THRESHOLDS.homeResources);
    expect(metrics.scripts).toBeLessThan(THRESHOLDS.scriptResources);
    expect(metrics.styles).toBeLessThan(THRESHOLDS.styleResources);
  });

  test('真实报告页资源数量应该保持在当前合理范围', async ({ page }) => {
    await injectAuthToken(page, authToken);
    await page.goto(`/report/${reportTaskId}`);
    await page.waitForLoadState('networkidle');

    const metrics = await getPerformanceMetrics(page);
    expect(metrics.resources).toBeLessThan(THRESHOLDS.reportResources);
    expect(metrics.scripts).toBeLessThan(THRESHOLDS.scriptResources);
  });

  test('首页内存使用应该保持在当前合理范围', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const memoryInfo = await page.evaluate(() => {
      if (!('memory' in performance)) {
        return null;
      }

      const metrics = (performance as Performance & {
        memory?: {
          usedJSHeapSize: number;
        };
      }).memory;

      return metrics ? metrics.usedJSHeapSize / 1024 / 1024 : null;
    });

    if (memoryInfo !== null) {
      expect(memoryInfo).toBeLessThan(THRESHOLDS.memoryMb);
    }
  });
});
