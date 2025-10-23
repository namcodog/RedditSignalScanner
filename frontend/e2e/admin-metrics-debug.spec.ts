/**
 * Admin Dashboard - 数据质量 Tab 调试测试
 * 
 * 用于调试为什么点击事件不触发
 */

import { test, expect } from '@playwright/test';

test.describe('Admin Dashboard - 调试测试', () => {
  test('调试：检查按钮点击事件', async ({ page }) => {
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');
    
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 截图：初始状态
    await page.screenshot({ path: 'test-results/debug-01-initial.png' });
    
    // 获取"数据质量" Tab 按钮
    const metricsButton = page.getByRole('button', { name: '数据质量' });
    
    // 验证按钮存在
    await expect(metricsButton).toBeVisible();
    console.log('✅ 按钮可见');
    
    // 验证按钮可点击
    await expect(metricsButton).toBeEnabled();
    console.log('✅ 按钮可点击');
    
    // 获取按钮的初始样式
    const initialBorderColor = await metricsButton.evaluate(el => 
      window.getComputedStyle(el).borderBottomColor
    );
    console.log('初始边框颜色:', initialBorderColor);
    
    // 点击按钮
    console.log('点击"数据质量" Tab...');
    await metricsButton.click();
    
    // 等待一下
    await page.waitForTimeout(1000);
    
    // 截图：点击后
    await page.screenshot({ path: 'test-results/debug-02-after-click.png' });
    
    // 获取点击后的样式
    const afterBorderColor = await metricsButton.evaluate(el => 
      window.getComputedStyle(el).borderBottomColor
    );
    console.log('点击后边框颜色:', afterBorderColor);
    
    // 检查页面内容
    const pageContent = await page.content();
    const hasMetricsHeading = pageContent.includes('数据质量看板');
    console.log('页面是否包含"数据质量看板":', hasMetricsHeading);
    
    // 检查是否有 API 请求
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/api/metrics')) {
        requests.push(request.url());
        console.log('捕获到 API 请求:', request.url());
      }
    });
    
    // 再次点击
    console.log('再次点击"数据质量" Tab...');
    await metricsButton.click();
    await page.waitForTimeout(2000);
    
    console.log('API 请求数量:', requests.length);
    
    // 截图：最终状态
    await page.screenshot({ path: 'test-results/debug-03-final.png' });
  });

  test('调试：使用 JavaScript 直接触发点击', async ({ page }) => {
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');
    await page.waitForLoadState('networkidle');
    
    // 使用 JavaScript 直接触发点击
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const metricsButton = buttons.find(b => b.textContent === '数据质量');
      if (metricsButton) {
        console.log('找到按钮，触发点击');
        metricsButton.click();
      } else {
        console.log('未找到按钮');
      }
    });
    
    // 等待
    await page.waitForTimeout(2000);
    
    // 截图
    await page.screenshot({ path: 'test-results/debug-04-js-click.png' });
    
    // 检查页面内容
    const pageContent = await page.content();
    const hasMetricsHeading = pageContent.includes('数据质量看板');
    console.log('使用 JS 点击后，页面是否包含"数据质量看板":', hasMetricsHeading);
  });

  test('调试：检查 React 组件状态', async ({ page }) => {
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');
    await page.waitForLoadState('networkidle');
    
    // 检查 React 组件是否正确渲染
    const hasReactRoot = await page.evaluate(() => {
      const root = document.querySelector('#root');
      return !!root && root.children.length > 0;
    });
    console.log('React 根节点是否存在:', hasReactRoot);
    
    // 检查按钮的事件监听器
    const buttonInfo = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const metricsButton = buttons.find(b => b.textContent === '数据质量');
      if (!metricsButton) return { found: false };
      
      return {
        found: true,
        tagName: metricsButton.tagName,
        textContent: metricsButton.textContent,
        hasOnClick: !!metricsButton.onclick,
        attributes: Array.from(metricsButton.attributes).map(attr => ({
          name: attr.name,
          value: attr.value
        }))
      };
    });
    console.log('按钮信息:', JSON.stringify(buttonInfo, null, 2));
  });
});

