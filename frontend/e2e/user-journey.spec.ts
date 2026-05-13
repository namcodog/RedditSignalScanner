import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

import {
  createUniqueEmail,
  injectAuthToken,
  registerUserViaApi,
} from './helpers/current-world';

const TEST_PASSWORD = 'TestPass123!';

const readAuthTokenSafely = async (page: Page): Promise<string | null> => {
  try {
    return await page.evaluate(() => window.localStorage.getItem('auth_token'));
  } catch {
    return null;
  }
};

const waitForAuthToken = async (page: Page) => {
  await expect.poll(async () => readAuthTokenSafely(page), { timeout: 15000 }).not.toBeNull();
};

const openAuthDialog = async (page: Page, mode: 'login' | 'register') => {
  await page.goto('/');
  await page.getByRole('button', { name: mode === 'login' ? '登录' : '注册', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
};

const submitRegisterForm = async (
  page: Page,
  options: { email: string; password: string; name?: string },
) => {
  const dialog = page.getByRole('dialog');
  await dialog.locator('#register-name').fill(options.name ?? '测试用户');
  await dialog.locator('#register-email').fill(options.email);
  await dialog.locator('#register-password').fill(options.password);
  await dialog.locator('form').getByRole('button', { name: '注册', exact: true }).click();
};

const submitLoginForm = async (
  page: Page,
  options: { email: string; password: string },
) => {
  const dialog = page.getByRole('dialog');
  await dialog.locator('#login-email').fill(options.email);
  await dialog.locator('#login-password').fill(options.password);
  await dialog.locator('form').getByRole('button', { name: '登录', exact: true }).click();
};

test.describe('用户完整旅程测试', () => {
  test('应该通过当前认证弹窗成功注册新用户', async ({ page }) => {
    const email = createUniqueEmail('journey-register');

    await openAuthDialog(page, 'register');
    await submitRegisterForm(page, { email, password: TEST_PASSWORD });

    await waitForAuthToken(page);
    await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible();
  });

  test('应该拒绝重复邮箱注册', async ({ page, request }) => {
    const email = createUniqueEmail('journey-duplicate');
    await registerUserViaApi(request, {
      email,
      password: TEST_PASSWORD,
      membershipLevel: 'free',
    });

    await openAuthDialog(page, 'register');
    await submitRegisterForm(page, { email, password: TEST_PASSWORD });

    await expect(page.getByRole('dialog').getByText(/操作冲突|邮箱已被注册|注册失败/)).toBeVisible();
  });

  test('应该通过当前认证弹窗成功登录已存在用户', async ({ page, request }) => {
    const email = createUniqueEmail('journey-login');
    await registerUserViaApi(request, {
      email,
      password: TEST_PASSWORD,
      membershipLevel: 'pro',
    });

    await openAuthDialog(page, 'login');
    await submitLoginForm(page, { email, password: TEST_PASSWORD });

    await waitForAuthToken(page);
    await expect(page.getByText('欢迎回来')).toBeVisible();
    await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible();
  });

  test('应该拒绝错误密码登录', async ({ page, request }) => {
    const email = createUniqueEmail('journey-wrong-password');
    await registerUserViaApi(request, {
      email,
      password: TEST_PASSWORD,
      membershipLevel: 'free',
    });

    await openAuthDialog(page, 'login');
    await submitLoginForm(page, { email, password: 'WrongPassword123!' });

    await expect(page.getByRole('dialog').getByText(/登录失败|登录已过期|邮箱和密码/)).toBeVisible();
    await expect.poll(async () => readAuthTokenSafely(page), { timeout: 15000 }).toBeNull();
  });

  test('应该在当前输入页成功提交任务并进入分析流程', async ({ page, request }) => {
    const email = createUniqueEmail('journey-submit');
    const token = await registerUserViaApi(request, {
      email,
      password: TEST_PASSWORD,
      membershipLevel: 'pro',
    });

    await injectAuthToken(page, token);
    await page.goto('/');

    const textarea = page.getByRole('textbox', { name: '产品描述' });
    await expect(textarea).toBeVisible();
    await textarea.fill('一款帮助自由职业者管理时间和发票的 SaaS 工具，自动追踪工时并生成专业发票。');

    await expect(page.getByText('字数适合分析')).toBeVisible();
    await page.getByRole('button', { name: '开始 5 分钟分析' }).click();

    await page.waitForURL(/\/(progress|report)\//, { timeout: 15000 });

    if (page.url().includes('/progress/')) {
      await expect(page.getByRole('heading', { name: '正在分析您的产品' })).toBeVisible();
      await expect(page.getByRole('heading', { name: '正在分析的产品' })).toBeVisible();
      await expect(page.getByRole('heading', { name: '分析进度' })).toBeVisible();
    } else {
      await expect(
        page.getByRole('heading', { name: /这次(已经值得继续做|先判断要不要放大)/, level: 2 }),
      ).toBeVisible();
    }
  });

  test('应该阻止空描述直接提交', async ({ page, request }) => {
    const email = createUniqueEmail('journey-empty');
    const token = await registerUserViaApi(request, {
      email,
      password: TEST_PASSWORD,
      membershipLevel: 'pro',
    });

    await injectAuthToken(page, token);
    await page.goto('/');

    await expect(page.getByRole('button', { name: '开始 5 分钟分析' })).toBeDisabled();
    await expect(page.getByText('还需要至少 10 个字')).toBeVisible();
  });

  test('应该阻止过短描述提交', async ({ page, request }) => {
    const email = createUniqueEmail('journey-short');
    const token = await registerUserViaApi(request, {
      email,
      password: TEST_PASSWORD,
      membershipLevel: 'pro',
    });

    await injectAuthToken(page, token);
    await page.goto('/');

    const textarea = page.getByRole('textbox', { name: '产品描述' });
    await textarea.fill('太短了');

    await expect(page.getByText('至少需要 10 个字符')).toBeVisible();
    await expect(page.getByRole('button', { name: '开始 5 分钟分析' })).toBeDisabled();
  });
});
