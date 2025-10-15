/**
 * ReportPage 端到端测试 - 简化版（Day 7 验收）
 *
 * 基于 PRD-08 端到端测试规范 & Day 7 验收标准
 * 最后更新: 2025-10-11 Day 7
 *
 * 测试范围：
 * - 报告页面错误处理（不存在的任务）
 * - 导航功能
 *
 * 注意：使用真实 Backend API，通过 API 直接获取认证 token
 */

import { test, expect, request } from '@playwright/test';

// 全局变量存储认证 token
let globalAuthToken: string;

// 在所有测试前获取认证 token
test.beforeAll(async ({ }, testInfo) => {
  const apiContext = await request.newContext({
    baseURL: 'http://localhost:8006',
  });

  try {
    // 使用 worker index 和时间戳确保邮箱唯一性
    const tempEmail = `test-e2e-w${testInfo.workerIndex}-${Date.now()}-${Math.random().toString(36).substring(7)}@example.com`;
    const tempPassword = `TestPass${Date.now()}!`;

    console.log('🔐 注册测试用户:', tempEmail);

    const registerResponse = await apiContext.post('/api/auth/register', {
      data: {
        email: tempEmail,
        password: tempPassword,
      },
    });

    if (!registerResponse.ok()) {
      const errorText = await registerResponse.text();
      throw new Error(`注册失败 (${registerResponse.status()}): ${errorText}`);
    }

    const registerData = await registerResponse.json();
    globalAuthToken = registerData.access_token;
    console.log('✅ 获取到认证 token');

  } catch (error) {
    console.error('❌ 注册用户失败:', error);
    throw error;
  } finally {
    await apiContext.dispose();
  }
});

test.describe('ReportPage - 错误处理 (真实 API)', () => {
  test.beforeEach(async ({ page }) => {
    // 访问首页并注入 token
    await page.goto('http://localhost:3008');
    await page.evaluate((token) => {
      localStorage.setItem('auth_token', token);
    }, globalAuthToken);
    console.log('✅ 已注入认证 token 到 localStorage');
  });

  test('不存在的任务应该显示错误状态', async ({ page }) => {
    // 访问一个不存在的任务
    await page.goto('http://localhost:3008/report/non-existent-task-id-12345');

    // 等待页面加载完成
    await page.waitForLoadState('networkidle');

    // 验证错误消息（使用 heading role 避免 strict mode 错误）
    await expect(page.getByRole('heading', { name: '获取报告失败' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /返回首页/ })).toBeVisible();
  });

  test('点击错误页面的"返回首页"应该跳转到首页', async ({ page }) => {
    // 访问一个不存在的任务
    await page.goto('http://localhost:3008/report/non-existent-task-id-67890');

    // 等待页面加载完成
    await page.waitForLoadState('networkidle');

    // 验证错误消息（使用 heading role 避免 strict mode 错误）
    await expect(page.getByRole('heading', { name: '获取报告失败' })).toBeVisible({ timeout: 10000 });

    // 点击返回首页按钮
    const backButton = page.getByRole('button', { name: /返回首页/ });
    await expect(backButton).toBeVisible();
    await backButton.click();

    // 验证跳转到首页
    await expect(page).toHaveURL('http://localhost:3008/');
  });
});

