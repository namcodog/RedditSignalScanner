import { expect, test } from '@playwright/test';

import {
  createUniqueEmail,
  injectAuthToken,
  registerUserViaApi,
} from './helpers/current-world';

test.describe('ReportPage - 当前错误态', () => {
  let authToken = '';

  test.beforeAll(async ({ request }) => {
    authToken = await registerUserViaApi(request, {
      email: createUniqueEmail('report-error'),
      password: 'TestPass123!',
      membershipLevel: 'pro',
    });
  });

  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page, authToken);
  });

  test('不存在的任务应该显示当前产品化错误状态', async ({ page }) => {
    await page.goto('/report/non-existent-task-id-12345');
    const statePanel = page.getByTestId('product-state-panel');

    await expect(page.getByRole('heading', { name: '这份结果还在整理中' })).toBeVisible();
    await expect(statePanel.getByRole('button', { name: '重新加载' })).toBeVisible();
    await expect(statePanel.getByRole('button', { name: '返回首页' })).toBeVisible();
    await expect(
      page.getByText('先重载一次；还不行就回首页重跑。'),
    ).toBeVisible();
  });

  test('点击错误页返回首页后应该回到输入页', async ({ page }) => {
    await page.goto('/report/non-existent-task-id-67890');
    const statePanel = page.getByTestId('product-state-panel');

    await expect(page.getByRole('heading', { name: '这份结果还在整理中' })).toBeVisible();
    await statePanel.getByRole('button', { name: '返回首页' }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole('heading', { name: '描述您的产品想法' })).toBeVisible();
  });
});
