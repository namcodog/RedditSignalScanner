# Phase 448 - 报告正文排版修复与卡片层级精修

## 发现了什么？

- 用户这轮指出了两个真实问题：
  1. 报告详情页的卡片层级还不够细，部分灰色卡片突兀，字号偏大，整体节奏不协调。
  2. 完整报告页其实没有被“渲染”，而是在很多情况下直接把 markdown 当原始文本吐出来，所以出现：
    - `## 1. 开篇概览`
    - `**需求趋势**`
    - 正文显示像原始草稿，不像报告
- 当前根因不是内容没生成，而是前端没有把 markdown 结构化渲染出来。
- 同时，标准报告页和真实 `ReportPage` 的“完整报告”入口也不是同一套交付：
  - 标准报告页会在 tab 里吐 raw markdown / html
  - 真实报告页甚至会新开窗口直接写入原始文档

## 是否需要修复？

- 需要，而且这轮就是先收这个。
- 这不是 cosmetic polish，而是把“完整报告”从原始文档输出改成真正可读的产品页面。

## 精确修复方法

### 1. 抽出共享的报告 markdown 解析器和正文组件

- 新增文件：
  - [report-markdown.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/report-markdown.ts)
  - [EditorialReportDocument.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/components/report/EditorialReportDocument.tsx)
- 作用：
  - 解析 `# 标题`
  - 解析 `## 1. ...` 到 `## 7. ...` 的章节
  - 把 `**需求趋势**` 这类小标题渲染成真正的层级标题
  - 不再让正文以 raw markdown 的形式暴露给用户

### 2. 标准报告页卡片层级精修

- 文件：[StandardReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/StandardReportPage.tsx)
- 处理：
  - 卡片页所有核心字号整体收一档
  - 原先突兀的灰色 ghost 卡改成更轻的暖色 accent surface
  - 用 markdown 的章节标题回填卡片章节标题，确保卡片与正文的章节命名一致

### 3. 标准报告页完整报告 tab 改成真正正文

- 文件：[StandardReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/StandardReportPage.tsx)
- 处理：
  - 去掉 raw `pre` 呈现
  - 改为使用共享 `EditorialReportDocument`
  - 完整报告现在按 `1 -> 7` 章节顺序展示，和卡片版颗粒度对齐

### 4. 真实 `ReportPage` 的完整报告入口也改成页内正文

- 文件：[ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)
- 处理：
  - `看完整报告` 不再 `window.open()` 新窗口吐原始文档
  - 新增页内 `full-report` 视图
  - 同样复用共享正文组件

### 5. 样式补齐

- 文件：[index.css](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/styles/index.css)
- 新增：
  - `editorial-card-accent`
  - `editorial-reading-surface`
  - `editorial-reading-html`
- 目标：
  - 把正文和次级卡片都收进同一套 warm editorial 语言

## 验证

- `cd frontend && npm test -- src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/ReportPage.test.tsx`
  - `8 passed`
- `cd frontend && npm run build`
  - 通过
- Playwright 真实浏览器确认：
  - `http://127.0.0.1:3006/standard-report/cross-border-paypal?view=report`
  - 完整报告已从 raw markdown 变成真正章节流
  - `##` / `**` 这类原始标记不再直接暴露
  - 卡片页字号和表面层级已收细

## 下一步系统性的计划是什么？

1. 继续按用户节奏做前端真实验收，收剩下的“内容脏点”和局部视觉问题。
2. 如果用户确认标准报告页这一套节奏成立，再把真实报告页的欢迎页 / selector / detail 也继续往同一套章节阅读体验收。
3. 再处理内容层问题，例如个别机会卡卖点出现碎词、个别社区卡样本质量偏脏。

## 这次执行的价值是什么？

- 这轮把“完整报告”从原始文本输出修成了真正的产品正文。
- 现在用户看到的是：
  - 卡片版和正文版同一套章节
  - 同一套信息颗粒度
  - 同一套阅读顺序
- 这一步解决的是报告页最影响感知的那层问题：它终于更像报告，而不是原始 markdown 导出结果。
