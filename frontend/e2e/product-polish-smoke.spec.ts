import { execFileSync } from 'node:child_process';
import path from 'node:path';

import { expect, test } from '@playwright/test';

import {
  createAcceptanceTokenForUser,
  findLatestRealReportSample,
  injectAuthToken,
} from './helpers/current-world';

const repoRoot = path.resolve(process.cwd(), '..');

const createLiveHotpostResultUrl = (): string => {
  const raw = execFileSync(
    'python',
    [
      'backend/scripts/acceptance/run_live_hotpost_acceptance.py',
      '--timeout-seconds',
      '120',
      '--request-timeout-seconds',
      '60',
      '--request-retry-attempts',
      '3',
    ],
    {
      cwd: repoRoot,
      encoding: 'utf-8',
    },
  ).trim();
  const payload = JSON.parse(raw) as { result_url: string };
  const liveUrl = new URL(payload.result_url);
  liveUrl.hostname = 'localhost';
  liveUrl.port = process.env.PLAYWRIGHT_FRONTEND_PORT ?? liveUrl.port;
  return liveUrl.toString();
};

test.describe.serial('Product Polish Smoke E2E', () => {
  let authToken: string;
  let reportTaskId = '';

  test.beforeAll(async () => {
    const reportSample = findLatestRealReportSample();
    authToken = createAcceptanceTokenForUser(reportSample.userId, reportSample.userEmail);
    reportTaskId = reportSample.taskId;
  });

  test('report 真实样本页应该展示新的判断节奏', async ({ page }) => {
    await injectAuthToken(page, authToken);

    await page.goto(`/report/${reportTaskId}`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: '这次已经值得继续做', level: 2 })).toBeVisible();
    await expect(page.getByRole('heading', { name: '支持拍板的 3 条证据', level: 2 })).toBeVisible();
    await expect(page.getByText('先扫这三条就够；不够再往下拆。')).toBeVisible();
    await expect(page.getByText('先挑最影响拍板的一块看。')).toBeVisible();
  });

  test('hotpost live 结果页应该展示新的快扫节奏', async ({ page }) => {
    const hotpostResultUrl = createLiveHotpostResultUrl();
    await page.goto(hotpostResultUrl, { waitUntil: 'domcontentloaded' });

    await expect(
      page.getByRole('heading', { name: /这波(先决定追不追|值得马上继续追)/, level: 2 }),
    ).toBeVisible();
    await expect(page.getByRole('heading', { name: '这页先看三件事', level: 2 })).toBeVisible();
    await expect(page.getByText('先看摘要', { exact: true })).toBeVisible();
    await expect(page.getByText('再扫证据', { exact: true })).toBeVisible();
    await expect(page.getByText('最后看社区', { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: '这波主要出在哪些社区', level: 3 })).toBeVisible();
  });
});
