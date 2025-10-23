/**
 * Admin Dashboard - 渲染调试测试
 * 
 * 检查 MetricsTab 组件为什么不渲染
 */

import { test, expect } from '@playwright/test';

test.describe('Admin Dashboard - 渲染调试', () => {
  test('检查 activeTab 状态和组件渲染', async ({ page }) => {
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');
    await page.waitForLoadState('networkidle');
    
    // 点击"数据质量" Tab
    await page.getByRole('button', { name: '数据质量' }).click();
    await page.waitForTimeout(1000);
    
    // 检查 DOM 结构
    const domInfo = await page.evaluate(() => {
      // 获取所有 Tab 按钮
      const buttons = Array.from(document.querySelectorAll('button'));
      const tabButtons = buttons.filter(b => 
        ['社区验收', '算法验收', '用户反馈', '数据质量'].includes(b.textContent || '')
      );
      
      // 检查哪个按钮是激活状态（蓝色边框）
      const activeButton = tabButtons.find(b => {
        const style = window.getComputedStyle(b);
        return style.borderBottomColor === 'rgb(59, 130, 246)';
      });
      
      // 获取页面主要内容
      const root = document.querySelector('#root');
      const allText = root?.textContent || '';
      
      // 检查是否有 MetricsTab 的特征文本
      const hasMetricsHeading = allText.includes('数据质量看板');
      const hasCommunityContent = allText.includes('社区名');
      const hasAlgorithmContent = allText.includes('算法验收');
      
      return {
        activeButtonText: activeButton?.textContent || 'none',
        hasMetricsHeading,
        hasCommunityContent,
        hasAlgorithmContent,
        rootChildrenCount: root?.children.length || 0,
        allTextLength: allText.length
      };
    });
    
    console.log('DOM 信息:', JSON.stringify(domInfo, null, 2));
    
    // 验证
    expect(domInfo.activeButtonText).toBe('数据质量');
    
    // 如果 MetricsTab 没有渲染，检查是否还在显示其他 Tab 的内容
    if (!domInfo.hasMetricsHeading) {
      console.log('❌ MetricsTab 没有渲染');
      console.log('是否显示社区内容:', domInfo.hasCommunityContent);
      console.log('是否显示算法内容:', domInfo.hasAlgorithmContent);
    }
  });

  test('检查所有 Tab 的切换', async ({ page }) => {
    // 访问 Admin 页面
    await page.goto('http://localhost:3006/admin');
    await page.waitForLoadState('networkidle');
    
    const tabs = ['社区验收', '算法验收', '用户反馈', '数据质量'];
    const results = [];
    
    for (const tabName of tabs) {
      // 点击 Tab
      await page.getByRole('button', { name: tabName }).click();
      await page.waitForTimeout(500);
      
      // 检查渲染结果
      const info = await page.evaluate((name) => {
        const root = document.querySelector('#root');
        const allText = root?.textContent || '';
        
        return {
          tabName: name,
          hasContent: allText.length > 1000,
          contentPreview: allText.substring(0, 200)
        };
      }, tabName);
      
      results.push(info);
      console.log(`Tab "${tabName}":`, info.hasContent ? '✅ 有内容' : '❌ 无内容');
    }
    
    // 打印所有结果
    console.log('\n所有 Tab 切换结果:');
    results.forEach(r => {
      console.log(`- ${r.tabName}: ${r.hasContent ? '✅' : '❌'}`);
    });
  });
});

