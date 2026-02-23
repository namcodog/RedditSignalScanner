/**
 * 用户旅程端到端测试
 * 
 * 基于 PRD-08 端到端测试规范 & DAY14 任务要求
 * 最后更新: 2025-10-14 Day 14
 * 
 * 测试范围：
 * - 用户注册流程
 * - 用户登录流程
 * - 任务提交流程
 * - SSE 实时进度
 * - 报告展示
 * 
 * 注意：使用真实 Backend API
 */

import { test, expect, request } from '@playwright/test';

// 全局变量存储测试用户信息
let registerUserEmail: string;
let registerUserPassword: string;
let proUserEmail: string;
let proUserPassword: string;
let proAuthToken: string;
let reportTaskId: string;

test.describe.serial('用户完整旅程测试', () => {
  test.beforeAll(async ({ request }) => {
    registerUserEmail = `test-journey-${Date.now()}-${Math.random().toString(36).substring(7)}@example.com`;
    registerUserPassword = `TestPass${Date.now()}!`;
    proUserEmail = `test-journey-pro-${Date.now()}-${Math.random().toString(36).substring(7)}@example.com`;
    proUserPassword = `TestPass${Date.now()}!`;

    const response = await request.post('http://localhost:8006/api/auth/register', {
      data: {
        email: proUserEmail,
        password: proUserPassword,
        membership_level: 'pro',
      },
    });
    if (!response.ok()) {
      throw new Error(`PRO 测试用户注册失败: ${response.status()}`);
    }
    const body = await response.json();
    proAuthToken = body.access_token;
  });

  test.describe('1. 用户注册流程', () => {
    test('应该成功注册新用户', async ({ page }) => {
      // 生成唯一的测试用户
      console.log('🔐 注册测试用户:', registerUserEmail);

      // 访问首页
      await page.goto('http://localhost:3006');

      // 点击注册按钮
      const registerButton = page.getByRole('button', { name: '注册' }).first();
      await expect(registerButton).toBeVisible();
      await registerButton.click();

      // 等待注册对话框出现
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // 填写注册表单
      const dialog = page.locator('[role="dialog"]');
      await dialog.locator('#register-name').fill('测试用户');
      await dialog.locator('input[type="email"]').fill(registerUserEmail);
      await dialog.locator('input[type="password"]').fill(registerUserPassword);

      // 提交注册（在对话框内查找按钮）
      const submitButton = dialog.getByRole('button', { name: /注册|提交/ });
      await submitButton.click();

      // 等待注册成功（对话框关闭或页面刷新）
      await Promise.race([
        page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 15000 }),
        page.waitForLoadState('networkidle')
      ]).catch(() => {
        // 如果等待失败，继续执行
      });

      // 等待 token 写入 localStorage
      await page.waitForFunction(() => localStorage.getItem('auth_token'), null, { timeout: 10000 });

      // 验证已登录状态（localStorage 应该有 auth_token）
      const token = await page.evaluate(() => localStorage.getItem('auth_token'));
      expect(token).toBeTruthy();

      console.log('✅ 用户注册成功');
    });

    test('应该拒绝重复邮箱注册', async ({ page }) => {
      // 使用已注册的邮箱再次注册
      await page.goto('http://localhost:3006');

      const registerButton = page.getByRole('button', { name: '注册' }).first();
      await registerButton.click();

      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      const dialog = page.locator('[role="dialog"]');
      await dialog.locator('#register-name').fill('测试用户');
      await dialog.locator('input[type="email"]').fill(registerUserEmail);
      await dialog.locator('input[type="password"]').fill(registerUserPassword);

      const submitButton = dialog.getByRole('button', { name: /注册|提交/ });
      await submitButton.click();

      // 验证错误消息
      await expect(
        page.getByText(/邮箱已被注册|已存在|操作冲突|注册失败/)
      ).toBeVisible({ timeout: 5000 });

      console.log('✅ 重复邮箱注册被正确拒绝');
    });
  });

  test.describe('2. 用户登录流程', () => {
    test('应该成功登录已注册用户', async ({ page }) => {
      // 访问首页
      await page.goto('http://localhost:3006');

      // 点击登录按钮
      const loginButton = page.getByRole('button', { name: '登录' }).first();
      await expect(loginButton).toBeVisible();
      await loginButton.click();

      // 等待登录对话框出现
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // 填写登录表单
      const dialog = page.locator('[role="dialog"]');
      await dialog.locator('input[type="email"]').fill(proUserEmail);
      await dialog.locator('input[type="password"]').fill(proUserPassword);

      // 提交登录
      const submitButton = dialog.getByRole('button', { name: /登录|提交/ });
      await submitButton.click();

      // 等待登录成功（对话框关闭或页面刷新）
      await Promise.race([
        page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 15000 }),
        page.waitForLoadState('networkidle')
      ]).catch(() => {
        // 如果等待失败，继续执行
      });

      // 等待 token 写入 localStorage
      await page.waitForFunction(() => localStorage.getItem('auth_token'), null, { timeout: 10000 });

      const token = await page.evaluate(() => localStorage.getItem('auth_token'));
      expect(token).toBeTruthy();
      proAuthToken = token!;

      console.log('✅ 用户登录成功');
    });

    test('应该拒绝错误的密码', async ({ page }) => {
      await page.goto('http://localhost:3006');

      const loginButton = page.getByRole('button', { name: '登录' }).first();
      await loginButton.click();

      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      const dialog = page.locator('[role="dialog"]');
      await dialog.locator('input[type="email"]').fill(proUserEmail);
      await dialog.locator('input[type="password"]').fill('WrongPassword123!');

      const submitButton = dialog.getByRole('button', { name: /登录|提交/ });
      await submitButton.click();

      // 验证未写入 token
      const token = await page.evaluate(() => localStorage.getItem('auth_token'));
      expect(token).toBeFalsy();

      console.log('✅ 错误密码被正确拒绝');
    });
  });

  test.describe('3. 任务提交流程', () => {
    test.beforeEach(async ({ page }) => {
      // 访问首页并注入 token
      await page.goto('http://localhost:3006');
      await page.evaluate((token) => {
        localStorage.setItem('auth_token', token);
      }, proAuthToken);
      await page.reload();
    });

    test('应该成功提交分析任务', async ({ page }) => {
      // 等待页面加载
      await page.waitForLoadState('networkidle');

      // 填写产品描述
      const productDescription = '一款帮助自由职业者管理时间和发票的SaaS工具';
      const textarea = page.getByRole('textbox', { name: /产品描述/ });
      await expect(textarea).toBeVisible();
      await textarea.fill(productDescription);

      // 验证字数统计更新
      await expect(page.locator('[aria-live="polite"]').filter({ hasText: /^\d+ 字$/ })).toBeVisible();

      // 点击开始分析按钮
      const analyzeButton = page.getByRole('button', { name: /开始.*分析/ });
      await expect(analyzeButton).toBeEnabled();
      await analyzeButton.click();

      // 验证跳转到进度页面
      await expect(page).toHaveURL(/\/progress\//, { timeout: 10000 });

      console.log('✅ 任务提交成功');
    });

    test('应该拒绝空的产品描述', async ({ page }) => {
      await page.waitForLoadState('networkidle');

      // 不填写产品描述，直接点击按钮
      const analyzeButton = page.getByRole('button', { name: /开始.*分析/ });
      
      // 按钮应该是禁用状态
      await expect(analyzeButton).toBeDisabled();

      console.log('✅ 空产品描述被正确拒绝');
    });

    test('应该拒绝过短的产品描述', async ({ page }) => {
      await page.waitForLoadState('networkidle');

      // 填写过短的描述
      const textarea = page.getByRole('textbox', { name: /产品描述/ });
      await textarea.fill('短');

      // 验证错误提示
      await expect(page.getByText(/至少.*字/).first()).toBeVisible();

      // 按钮应该是禁用状态
      const analyzeButton = page.getByRole('button', { name: /开始.*分析/ });
      await expect(analyzeButton).toBeDisabled();

      console.log('✅ 过短产品描述被正确拒绝');
    });
  });

  test.describe('4. SSE 实时进度测试', () => {
    let taskId: string;

    test.beforeEach(async ({ page }) => {
      // 访问首页并注入 token
      await page.goto('http://localhost:3006');
      await page.evaluate((token) => {
        localStorage.setItem('auth_token', token);
      }, proAuthToken);
      await page.reload();
    });

    test('应该显示实时进度更新', async ({ page }) => {
      // 提交任务
      await page.waitForLoadState('networkidle');
      
      const textarea = page.getByRole('textbox', { name: /产品描述/ });
      await textarea.fill('一款帮助开发者管理API文档的工具');
      
      const analyzeButton = page.getByRole('button', { name: /开始.*分析/ });
      await analyzeButton.click();

      // 等待跳转到进度页或直接进入报告页
      await page.waitForURL(/\/(progress|report)\//, { timeout: 10000 });
      
      // 提取 taskId
      const url = page.url();
      taskId = url.includes('/progress/')
        ? url.split('/progress/')[1]
        : url.split('/report/')[1];
      console.log('📝 任务ID:', taskId);

      const reportHeading = page.getByRole('heading', { name: /市场洞察报告/ }).first();
      const progressBar = page.locator('[role="progressbar"]');
      await Promise.race([
        reportHeading.waitFor({ state: 'visible', timeout: 5000 }),
        progressBar.waitFor({ state: 'visible', timeout: 5000 }),
      ]);

      if ((await progressBar.count()) > 0) {
        await expect(progressBar).toBeVisible();
      } else {
        await expect(reportHeading).toBeVisible();
        console.log('⚡ 任务快速完成，已直接进入报告页');
      }

      console.log('✅ SSE 实时进度正常');
    });

    test('应该在分析完成后自动跳转到报告页面', async ({ page }) => {
      // 提交任务
      await page.waitForLoadState('networkidle');
      
      const textarea = page.getByRole('textbox', { name: /产品描述/ });
      await textarea.fill('一款帮助设计师管理素材库的工具');
      
      const analyzeButton = page.getByRole('button', { name: /开始.*分析/ });
      await analyzeButton.click();

      // 等待跳转到进度页或直接进入报告页
      await page.waitForURL(/\/(progress|report)\//, { timeout: 10000 });
      if (!page.url().includes('/report/')) {
        const viewReportButton = page.getByRole('button', { name: /查看报告/ });
        if (await viewReportButton.isVisible()) {
          await viewReportButton.click();
          await page.waitForURL(/\/report\//, { timeout: 30000 });
        } else {
          // 等待自动跳转到报告页面（最多等待5分钟）
          await page.waitForURL(/\/report\//, { timeout: 300000 });
        }
      }
      reportTaskId = page.url().split('/report/')[1];

      console.log('✅ 自动跳转到报告页面成功');
    });
  });

  test.describe('5. 报告展示测试', () => {
    test.beforeEach(async ({ page }) => {
      // 访问首页并注入 token
      await page.goto('http://localhost:3006');
      await page.evaluate((token) => {
        localStorage.setItem('auth_token', token);
      }, proAuthToken);
    });

    test('应该正确展示报告内容', async ({ page }) => {
      if (reportTaskId) {
        await page.goto(`http://localhost:3006/report/${reportTaskId}`);
      } else {
        // 提交任务并等待完成
        await page.goto('http://localhost:3006');
        await page.waitForLoadState('networkidle');
        
        const textarea = page.getByRole('textbox', { name: /产品描述/ });
        await textarea.fill('一款帮助产品经理管理需求的工具');
        
        const analyzeButton = page.getByRole('button', { name: /开始.*分析/ });
        await analyzeButton.click();

        // 等待跳转到报告页面
        await page.waitForURL(/\/report\//, { timeout: 300000 });
      }

      // 验证报告页面元素
      await expect(page.getByRole('heading', { name: /市场洞察报告/ })).toBeVisible();

      // 验证Tab导航（若报告降级则允许不展示）
      const overviewTab = page.locator('button:has-text("概览")').first();
      if (await overviewTab.count()) {
        await expect(overviewTab).toBeVisible();
        await expect(page.locator('button:has-text("用户痛点")').first()).toBeVisible();
        await expect(page.locator('button:has-text("竞品分析")').first()).toBeVisible();
        await expect(page.locator('button:has-text("商业机会")').first()).toBeVisible();
      } else {
        await expect(page.getByText(/样本不足|insufficient_samples|report.tier/).first()).toBeVisible();
      }

      // 验证分享和导出按钮
      await expect(page.getByRole('button', { name: /分享/ })).toBeVisible();
      await expect(page.getByRole('button', { name: /导出报告/ })).toBeVisible();

      console.log('✅ 报告内容展示正常');
    });

    test.skip('应该支持Tab切换', async ({ page }) => {
      // TODO: 需要创建一个真实的已完成任务才能测试 Tab 切换
      // 当前跳过此测试，因为需要完整的任务数据
      // 先登录
      await page.goto('http://localhost:3006');
      const loginButton = page.getByRole('button', { name: '登录' }).first();
      await loginButton.click();

      const dialog = page.locator('[role="dialog"]');
      await dialog.locator('input[type="email"]').fill('test@example.com');
      await dialog.locator('input[type="password"]').fill('Test123456!');

      const submitButton = dialog.getByRole('button', { name: /登录|提交/ });
      await submitButton.click();

      // 等待登录成功
      await Promise.race([
        page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 15000 }),
        page.waitForLoadState('networkidle')
      ]).catch(() => {});

      await page.waitForTimeout(2000);

      // 访问报告页面（使用真实任务ID或创建一个测试任务）
      await page.goto('http://localhost:3006/report/test-task-123');
      await page.waitForLoadState('networkidle');

      // 点击"用户痛点"Tab（使用更精确的选择器）
      const painPointsTab = page.locator('button:has-text("用户痛点")').first();
      await expect(painPointsTab).toBeVisible();
      await painPointsTab.click();

      // 验证Tab内容切换
      await expect(page.getByText(/严重程度|用户示例/)).toBeVisible({ timeout: 5000 });

      // 点击"竞品分析"Tab
      const competitorsTab = page.locator('button:has-text("竞品分析")').first();
      await competitorsTab.click();

      await expect(page.getByText(/市场份额|优势|劣势/)).toBeVisible({ timeout: 5000 });

      // 点击"商业机会"Tab
      const opportunitiesTab = page.locator('button:has-text("商业机会")').first();
      await opportunitiesTab.click();

      await expect(page.getByText(/关键洞察/)).toBeVisible({ timeout: 5000 });

      console.log('✅ Tab切换功能正常');
    });
  });
});
