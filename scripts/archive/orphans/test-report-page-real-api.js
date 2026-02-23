#!/usr/bin/env node

/**
 * 使用 Chrome DevTools 测试 ReportPage - 无 Mock，真实 API
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const FRONTEND_URL = 'http://localhost:3008';
const BACKEND_URL = 'http://localhost:8006';

async function testReportPageWithRealAPI() {
  console.log('==========================================');
  console.log('ReportPage 真实 API 测试 - Chrome DevTools');
  console.log('==========================================\n');

  const browser = await puppeteer.launch({
    headless: false,
    devtools: true,
    args: ['--start-maximized'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  const apiCalls = [];
  const consoleMessages = [];

  // 监听网络请求
  page.on('request', request => {
    if (request.url().includes('/api/')) {
      const info = {
        method: request.method(),
        url: request.url(),
        headers: request.headers(),
      };
      apiCalls.push({ type: 'request', ...info });
      console.log(`📤 ${info.method} ${info.url}`);
    }
  });

  // 监听网络响应
  page.on('response', async response => {
    if (response.url().includes('/api/')) {
      const info = {
        status: response.status(),
        url: response.url(),
        headers: response.headers(),
      };
      
      try {
        const contentType = response.headers()['content-type'] || '';
        if (contentType.includes('application/json')) {
          const data = await response.json();
          info.data = data;
          console.log(`📥 ${info.status} ${info.url}`);
          console.log(`   数据:`, JSON.stringify(data, null, 2).substring(0, 300));
        }
      } catch (e) {
        console.log(`📥 ${info.status} ${info.url} (无法解析 JSON)`);
      }
      
      apiCalls.push({ type: 'response', ...info });
    }
  });

  // 监听控制台
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`🔴 Console ${msg.type()}: ${text}`);
    }
  });

  try {
    // 测试 1: 访问首页
    console.log('\n1️⃣ 测试首页...');
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle2' });
    console.log('✅ 首页加载成功\n');

    // 测试 2: 访问 ReportPage (不存在的任务)
    console.log('2️⃣ 测试 ReportPage (不存在的任务)...');
    await page.goto(`${FRONTEND_URL}/report/test-task-123`, { waitUntil: 'networkidle2' });
    
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const pageContent1 = await page.evaluate(() => {
      return {
        title: document.title,
        h2Text: document.querySelector('h2')?.textContent,
        hasError: !!document.querySelector('[role="alert"]'),
        errorText: document.querySelector('.text-destructive')?.textContent,
        bodyText: document.body.textContent.substring(0, 500),
      };
    });
    
    console.log('📄 页面内容:', JSON.stringify(pageContent1, null, 2));
    await page.screenshot({ path: 'test-results/chrome-devtools/report-not-found.png', fullPage: true });
    console.log('📸 截图: test-results/chrome-devtools/report-not-found.png\n');

    // 测试 3: 创建一个真实的分析任务
    console.log('3️⃣ 创建真实的分析任务...');
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle2' });
    
    // 输入产品描述
    const textarea = await page.$('textarea');
    if (textarea) {
      await textarea.type('一个面向远程团队的项目管理工具，集成 Slack 并自动跟踪任务时间');
      console.log('✅ 已输入产品描述');
      
      // 点击提交按钮
      const submitButton = await page.$('button[type="submit"]');
      if (submitButton) {
        await submitButton.click();
        console.log('✅ 已点击提交按钮');
        
        // 等待跳转到 ProgressPage
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 });
        const currentUrl = page.url();
        console.log('📍 当前 URL:', currentUrl);
        
        if (currentUrl.includes('/progress/')) {
          const taskId = currentUrl.split('/progress/')[1];
          console.log('✅ 已跳转到 ProgressPage, taskId:', taskId);
          
          await page.screenshot({ path: 'test-results/chrome-devtools/progress-page.png', fullPage: true });
          console.log('📸 截图: test-results/chrome-devtools/progress-page.png');
          
          // 等待分析完成 (最多 30 秒)
          console.log('\n⏳ 等待分析完成 (最多 30 秒)...');
          let completed = false;
          for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const url = page.url();
            if (url.includes('/report/')) {
              completed = true;
              console.log('✅ 分析完成，已跳转到 ReportPage');
              break;
            }
            if (i % 5 === 0) {
              console.log(`   等待中... ${i}秒`);
            }
          }
          
          if (completed) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const reportContent = await page.evaluate(() => {
              return {
                title: document.title,
                h2Text: document.querySelector('h2')?.textContent,
                hasExecutiveSummary: !!document.querySelector('h3:has-text("执行摘要")'),
                hasMetrics: document.querySelectorAll('.grid > div').length,
                bodyText: document.body.textContent.substring(0, 1000),
              };
            });
            
            console.log('\n📄 ReportPage 内容:', JSON.stringify(reportContent, null, 2));
            await page.screenshot({ path: 'test-results/chrome-devtools/report-page-real.png', fullPage: true });
            console.log('📸 截图: test-results/chrome-devtools/report-page-real.png');
          } else {
            console.log('⚠️  分析未在 30 秒内完成');
          }
        }
      }
    }

    // 生成报告
    console.log('\n4️⃣ 生成测试报告...');
    const report = {
      timestamp: new Date().toISOString(),
      apiCalls: apiCalls.length,
      consoleErrors: consoleMessages.filter(m => m.type === 'error').length,
      consoleWarnings: consoleMessages.filter(m => m.type === 'warning').length,
      apiCallDetails: apiCalls,
      consoleDetails: consoleMessages,
    };

    const reportPath = 'test-results/chrome-devtools/api-test-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`✅ 报告已保存: ${reportPath}`);

    console.log('\n==========================================');
    console.log('测试完成！');
    console.log('==========================================');
    console.log(`📊 API 调用: ${apiCalls.length}`);
    console.log(`🔴 Console 错误: ${report.consoleErrors}`);
    console.log(`⚠️  Console 警告: ${report.consoleWarnings}`);
    console.log('\n浏览器保持打开，按 Ctrl+C 关闭\n');

    // 保持浏览器打开
    await new Promise(() => {});

  } catch (error) {
    console.error('❌ 测试失败:', error);
    await browser.close();
    process.exit(1);
  }
}

testReportPageWithRealAPI();

