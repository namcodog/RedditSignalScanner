/**
 * Admin Dashboard - 数据质量 Tab 端到端测试
 * 
 * 测试目标：验证质量看板 v0 功能
 * - T008: 质量看板前端组件
 * - T009: 质量看板页面集成
 * 
 * 验收标准：
 * 1. 可以访问 Admin 页面
 * 2. 可以点击"数据质量" Tab
 * 3. 可以看到三项核心指标
 * 4. 可以看到历史数据表格
 * 5. API 调用成功
 */

import { test, expect } from '@playwright/test';

test.describe('Admin Dashboard - 数据质量 Tab', () => {
  test.beforeEach(async ({ page }) => {
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');

    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
  });

  test('应该显示 4 个 Tab 按钮', async ({ page }) => {
    // 验证 4 个 Tab 按钮存在
    await expect(page.getByRole('button', { name: '社区验收' })).toBeVisible();
    await expect(page.getByRole('button', { name: '算法验收' })).toBeVisible();
    await expect(page.getByRole('button', { name: '用户反馈' })).toBeVisible();
    await expect(page.getByRole('button', { name: '数据质量' })).toBeVisible();
  });

  test('应该能够点击"数据质量" Tab 并显示质量看板', async ({ page }) => {
    // 设置 API 响应监听（在点击之前）
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/metrics') && response.status() === 200,
      { timeout: 10000 }
    );

    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();

    // 等待 API 请求完成
    await responsePromise;

    // 验证标题显示
    await expect(page.getByRole('heading', { name: '数据质量看板 v0' })).toBeVisible();
  });

  test('应该显示三项核心指标卡片', async ({ page }) => {
    // 设置 API 响应监听（在点击之前）
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/metrics') && response.status() === 200,
      { timeout: 10000 }
    );

    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();

    // 等待数据加载
    await responsePromise;

    // 验证三个指标卡片（使用更精确的选择器）
    await expect(page.locator('div').filter({ hasText: /^采集成功率$/ }).first()).toBeVisible();
    await expect(page.locator('div').filter({ hasText: /^重复率$/ }).first()).toBeVisible();
    await expect(page.locator('div').filter({ hasText: /^处理耗时$/ }).first()).toBeVisible();

    // 验证指标值显示（使用正则匹配百分比和秒数）
    await expect(page.getByText(/\d+\.\d+%/).first()).toBeVisible(); // 采集成功率
    await expect(page.getByText(/\d+\.\d+s/).first()).toBeVisible(); // 处理耗时
  });

  test('应该显示历史数据表格', async ({ page }) => {
    // 设置 API 响应监听（在点击之前）
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/metrics') && response.status() === 200,
      { timeout: 10000 }
    );

    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();

    // 等待数据加载
    await responsePromise;

    // 验证表格标题
    await expect(page.getByRole('heading', { name: '历史数据（最近 7 天）' })).toBeVisible();

    // 验证表格列标题
    await expect(page.getByText('日期')).toBeVisible();
    await expect(page.getByRole('cell', { name: '采集成功率' })).toBeVisible();
    await expect(page.getByRole('cell', { name: '重复率' })).toBeVisible();
    await expect(page.getByText('处理耗时 P50')).toBeVisible();
    await expect(page.getByText('处理耗时 P95')).toBeVisible();
  });

  test('应该成功调用 API 并返回数据', async ({ page }) => {
    // 监听 API 请求
    const responsePromise = page.waitForResponse(response => 
      response.url().includes('/api/metrics') && response.status() === 200
    );
    
    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();
    
    // 等待 API 响应
    const response = await responsePromise;
    
    // 验证响应状态
    expect(response.status()).toBe(200);
    
    // 验证响应数据格式
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThan(0);
    
    // 验证数据结构
    const firstItem = data[0];
    expect(firstItem).toHaveProperty('date');
    expect(firstItem).toHaveProperty('collection_success_rate');
    expect(firstItem).toHaveProperty('deduplication_rate');
    expect(firstItem).toHaveProperty('processing_time_p50');
    expect(firstItem).toHaveProperty('processing_time_p95');
  });

  test('应该在 Tab 切换时更新样式', async ({ page }) => {
    // 获取"数据质量" Tab 按钮
    const metricsTab = page.getByRole('button', { name: '数据质量' });

    // 点击前，按钮应该不是激活状态（没有蓝色边框）
    const beforeClick = await metricsTab.evaluate(el =>
      window.getComputedStyle(el).borderBottomColor
    );

    // 设置 API 响应监听（在点击之前）
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/metrics') && response.status() === 200,
      { timeout: 10000 }
    );

    // 点击"数据质量" Tab
    await metricsTab.click();

    // 等待数据加载
    await responsePromise;
    
    // 点击后，按钮应该是激活状态（蓝色边框）
    const afterClick = await metricsTab.evaluate(el => 
      window.getComputedStyle(el).borderBottomColor
    );
    
    // 验证样式变化
    expect(beforeClick).not.toBe(afterClick);
  });

  test('应该在页面加载 < 2 秒内完成', async ({ page }) => {
    // 设置 API 响应监听（在点击之前）
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/metrics') && response.status() === 200,
      { timeout: 10000 }
    );

    const startTime = Date.now();

    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();

    // 等待数据加载完成
    await responsePromise;

    // 等待内容显示
    await expect(page.getByRole('heading', { name: '数据质量看板 v0' })).toBeVisible();

    const endTime = Date.now();
    const loadTime = endTime - startTime;

    // 验证加载时间 < 2 秒
    expect(loadTime).toBeLessThan(2000);
  });

  test('应该正确显示 7 天的历史数据', async ({ page }) => {
    // 设置 API 响应监听（在点击之前）
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/metrics') && response.status() === 200,
      { timeout: 10000 }
    );

    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();

    // 等待 API 响应
    const response = await responsePromise;

    // 获取响应数据
    const data = await response.json();

    // 验证返回 7 天数据
    expect(data.length).toBe(7);

    // 验证日期格式（YYYY-MM-DD）
    data.forEach((item: any) => {
      expect(item.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  });
});

