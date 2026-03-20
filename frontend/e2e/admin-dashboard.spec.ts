import { expect, test } from '@playwright/test';

import {
  injectAuthToken,
  loginSeededUserViaApi,
} from './helpers/current-world';

const ADMIN_EMAIL = 'admin@test.com';
const ADMIN_PASSWORD = 'Admin123!';

test.describe('Admin Dashboard - 当前控制面', () => {
  let adminToken = '';

  test.beforeAll(async ({ request }) => {
    adminToken = await loginSeededUserViaApi(request, {
      email: ADMIN_EMAIL,
      password: ADMIN_PASSWORD,
    });
  });

  test.beforeEach(async ({ page }) => {
    await injectAuthToken(page, adminToken);
  });

  test('应该展示当前控制面的主结构', async ({ page }) => {
    const statsResponse = page.waitForResponse(
      (response) => response.url().includes('/api/admin/dashboard/stats') && response.status() === 200,
    );
    const tasksResponse = page.waitForResponse(
      (response) => response.url().includes('/api/admin/tasks/recent') && response.status() === 200,
    );

    await page.goto('/admin');
    await Promise.all([statsResponse, tasksResponse]);

    await expect(page.getByRole('heading', { name: '系统控制面', level: 1 })).toBeVisible();
    await expect(page.getByRole('heading', { name: '今天先看什么', level: 3 })).toBeVisible();
    await expect(page.getByRole('heading', { name: '今天机器稳不稳', level: 3 })).toBeVisible();
    await expect(page.getByRole('heading', { name: '控制面捷径', level: 3 })).toBeVisible();
  });

  test('应该展示机器状态和任务账本入口', async ({ page }) => {
    await page.goto('/admin');

    await expect(page.getByText('活跃节点 (Workers)')).toBeVisible();
    await expect(page.getByText('今日完成任务')).toBeVisible();
    await expect(page.getByRole('link', { name: '看全部任务' })).toBeVisible();
    await expect(page.getByRole('link', { name: /审核候选社区/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /看社区池/ })).toBeVisible();
  });

  test('应该能从控制面进入任务账本', async ({ page }) => {
    await page.goto('/admin');

    await page.getByRole('link', { name: '看全部任务' }).click();
    await expect(page).toHaveURL(/\/admin\/tasks\/ledger/);
  });
});
