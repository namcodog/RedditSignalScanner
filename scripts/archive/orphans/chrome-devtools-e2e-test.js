#!/usr/bin/env node

/**
 * Day 7 端到端测试 - 使用 Chrome DevTools Protocol
 * 
 * 测试范围:
 * 1. 首页加载
 * 2. ProgressPage 实时统计卡片
 * 3. ReportPage 基础结构
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const FRONTEND_URL = 'http://localhost:3008';
const BACKEND_URL = 'http://localhost:8006';

async function runE2ETests() {
  console.log('==========================================');
  console.log('Day 7 端到端测试 - Chrome DevTools Protocol');
  console.log('==========================================\n');

  const browser = await puppeteer.launch({
    headless: false, // 显示浏览器窗口
    devtools: true,  // 打开 DevTools
    args: ['--start-maximized'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  const results = {
    timestamp: new Date().toISOString(),
    tests: [],
    passed: 0,
    failed: 0,
  };

  try {
    // 测试 1: 首页加载
    console.log('1️⃣ 测试首页加载...');
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle2' });
    
    const homePageTitle = await page.title();
    console.log(`   页面标题: ${homePageTitle}`);
    
    const hasInputForm = await page.$('textarea[placeholder*="产品"]') !== null;
    const hasSubmitButton = await page.$('button:has-text("开始")') !== null;
    
    if (hasInputForm) {
      console.log('   ✅ 产品描述输入框存在');
      results.tests.push({ name: '首页加载', status: 'passed' });
      results.passed++;
    } else {
      console.log('   ❌ 产品描述输入框不存在');
      results.tests.push({ name: '首页加载', status: 'failed' });
      results.failed++;
    }

    // 截图
    const screenshotDir = path.join(__dirname, '../test-results/chrome-devtools');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ 
      path: path.join(screenshotDir, '01-homepage.png'),
      fullPage: true 
    });
    console.log('   📸 截图已保存: test-results/chrome-devtools/01-homepage.png\n');

    // 测试 2: ProgressPage (如果有正在运行的任务)
    console.log('2️⃣ 测试 ProgressPage...');
    console.log('   ⚠️  需要手动触发分析任务');
    console.log('   请在浏览器中:');
    console.log('   1. 输入产品描述');
    console.log('   2. 点击"开始 5 分钟分析"');
    console.log('   3. 观察实时统计卡片\n');

    // 等待用户操作
    console.log('   ⏳ 等待 10 秒供用户操作...');
    await new Promise(resolve => setTimeout(resolve, 10000));

    // 检查是否在 ProgressPage
    const currentUrl = page.url();
    if (currentUrl.includes('/progress/')) {
      console.log('   ✅ 已跳转到 ProgressPage');
      
      // 检查实时统计卡片
      const statsCards = await page.$$('.grid.grid-cols-1.gap-4.md\\:grid-cols-3 > div');
      console.log(`   📊 找到 ${statsCards.length} 个统计卡片`);
      
      if (statsCards.length === 3) {
        console.log('   ✅ 实时统计卡片数量正确 (3个)');
        results.tests.push({ name: 'ProgressPage 实时统计', status: 'passed' });
        results.passed++;
      } else {
        console.log('   ❌ 实时统计卡片数量不正确');
        results.tests.push({ name: 'ProgressPage 实时统计', status: 'failed' });
        results.failed++;
      }

      await page.screenshot({ 
        path: path.join(screenshotDir, '02-progress-page.png'),
        fullPage: true 
      });
      console.log('   📸 截图已保存: test-results/chrome-devtools/02-progress-page.png\n');
    } else {
      console.log('   ⚠️  未跳转到 ProgressPage，跳过测试\n');
    }

    // 测试 3: ReportPage
    console.log('3️⃣ 测试 ReportPage...');
    console.log('   访问示例报告页面...');
    
    // 直接访问一个测试报告页面
    await page.goto(`${FRONTEND_URL}/report/test-task-123`, { waitUntil: 'networkidle2' });
    
    await page.screenshot({ 
      path: path.join(screenshotDir, '03-report-page.png'),
      fullPage: true 
    });
    console.log('   📸 截图已保存: test-results/chrome-devtools/03-report-page.png\n');

    // 生成测试报告
    console.log('4️⃣ 生成测试报告...');
    const reportContent = `# Day 7 Chrome DevTools 端到端测试报告

**日期**: ${new Date().toLocaleString('zh-CN')}
**测试工具**: Chrome DevTools Protocol (Puppeteer)
**测试范围**: ProgressPage + ReportPage

---

## 测试环境

- **Frontend**: ${FRONTEND_URL} ✅
- **Backend**: ${BACKEND_URL}
- **浏览器**: Chrome (Headless: false, DevTools: true)

---

## 测试结果

### 总览

- **通过**: ${results.passed}
- **失败**: ${results.failed}
- **总计**: ${results.tests.length}

### 详细结果

${results.tests.map((test, index) => `
${index + 1}. **${test.name}**: ${test.status === 'passed' ? '✅ 通过' : '❌ 失败'}
`).join('')}

---

## 截图

1. 首页: \`test-results/chrome-devtools/01-homepage.png\`
2. ProgressPage: \`test-results/chrome-devtools/02-progress-page.png\`
3. ReportPage: \`test-results/chrome-devtools/03-report-page.png\`

---

## 手动验证项

### ProgressPage
- [ ] 实时统计卡片显示 (发现的社区、已分析帖子、生成的洞察)
- [ ] 数字动态更新
- [ ] 进度条平滑过渡
- [ ] 步骤状态正确切换
- [ ] 时间格式正确

### ReportPage
- [ ] 加载状态显示
- [ ] 执行摘要展示
- [ ] 4个关键指标卡片
- [ ] 元数据显示
- [ ] Day 8 占位符

---

**测试人**: Frontend Agent
**测试时间**: ${new Date().toLocaleString('zh-CN')}
`;

    const reportPath = path.join(__dirname, '../reports/phase-log/DAY7-CHROME-DEVTOOLS-TEST.md');
    fs.writeFileSync(reportPath, reportContent);
    console.log(`   ✅ 测试报告已生成: ${reportPath}\n`);

    console.log('==========================================');
    console.log('测试完成！');
    console.log('==========================================\n');
    console.log('📊 测试总结:');
    console.log(`  - 通过: ${results.passed}`);
    console.log(`  - 失败: ${results.failed}`);
    console.log(`  - 总计: ${results.tests.length}\n`);
    console.log('🌐 浏览器窗口保持打开，请手动验证功能');
    console.log('   按 Ctrl+C 关闭浏览器\n');

    // 保持浏览器打开
    await new Promise(() => {});

  } catch (error) {
    console.error('❌ 测试失败:', error);
    await browser.close();
    process.exit(1);
  }
}

// 检查依赖
try {
  require.resolve('puppeteer');
} catch (e) {
  console.error('❌ 缺少依赖: puppeteer');
  console.error('请运行: npm install puppeteer');
  process.exit(1);
}

runE2ETests();

