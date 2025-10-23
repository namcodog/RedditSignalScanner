/**
 * Admin Dashboard - 控制台调试测试
 * 
 * 检查浏览器控制台错误
 */

import { test } from '@playwright/test';

test.describe('Admin Dashboard - 控制台调试', () => {
  test('检查控制台错误和警告', async ({ page }) => {
    const consoleMessages: string[] = [];
    const errors: string[] = [];
    
    // 监听控制台消息
    page.on('console', msg => {
      const text = `[${msg.type()}] ${msg.text()}`;
      consoleMessages.push(text);
      if (msg.type() === 'error' || msg.type() === 'warning') {
        errors.push(text);
      }
    });
    
    // 监听页面错误
    page.on('pageerror', error => {
      errors.push(`[PAGE ERROR] ${error.message}`);
    });
    
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');
    await page.waitForLoadState('networkidle');
    
    // 等待一下，让所有错误都显示出来
    await page.waitForTimeout(2000);
    
    // 打印所有控制台消息
    console.log('\n=== 控制台消息 ===');
    consoleMessages.forEach(msg => console.log(msg));
    
    // 打印错误
    console.log('\n=== 错误和警告 ===');
    if (errors.length === 0) {
      console.log('✅ 没有错误或警告');
    } else {
      errors.forEach(err => console.log(err));
    }
    
    // 点击"数据质量" Tab
    console.log('\n=== 点击"数据质量" Tab ===');
    await page.getByRole('button', { name: '数据质量' }).click();
    await page.waitForTimeout(2000);
    
    // 打印点击后的新消息
    console.log('\n=== 点击后的新消息 ===');
    const newMessages = consoleMessages.slice(-10);
    newMessages.forEach(msg => console.log(msg));
  });
});

