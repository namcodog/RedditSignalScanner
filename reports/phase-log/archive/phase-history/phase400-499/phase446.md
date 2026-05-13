# Phase 446 - 标准报告页改成 1 到 7 纵向章节卡片

## 发现了什么？

- 用户在前端真实验收里明确指出，当前标准报告页的“卡片版”虽然信息够多，但视觉节奏是横向拼盘，读起来发散。
- 当前页面最该保留的是顶部封面区：
  - `Standard Report`
  - 标题
  - prompt 描述
  - 校验 chip
  - 4 个 summary 指标
- 最该删掉的是顶部右侧的“阅读方法”说明块：
  - 它不创造判断价值
  - 反而占用了首屏最宝贵的位置
- 真正需要的不是再讲“怎么读”，而是把页面本身排成自然的阅读顺序：
  1. 开篇概览
  2. 决策风向标
  3. 概览（市场健康度诊断）
  4. 核心战场推荐（画像分级）
  5. 用户痛点拆解
  6. 关键决策驱动力
  7. 商业机会

## 是否需要修复？

- 需要，而且这是当前前端报告页的最高优先级。
- 这次先不碰报告内容生成逻辑，只改“显示结构设计”，让前端阅读顺序先稳定下来。

## 精确修复方法

### 1. 标准报告页卡片版重排成 1 到 7 纵向章节

- 文件：[StandardReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/StandardReportPage.tsx)
- 处理：
  - 保留顶部封面区的整体风格
  - 删除右上角 `阅读方法`
  - 删除中间那块横向的 `DecisionSummaryPanel`
  - 删除“市场健康度 / 核心战场 / 痛点 / 驱动力与机会”几块横向拼接布局
  - 改成按 1 到 7 顺序，自上而下逐段展示

### 2. 保留风格，但补术语解释交互

- 新增 `?` 术语解释触点：
  - 战场
  - 驱动力
  - 机会
- 行为：
  - hover 时显示解释
  - focus / click 时也能显示
- 这样保留你认可的“边上有问号、看不懂就解释”的体验，但不再在页面上直接教用户“怎么读”

### 3. 更新样式，保证新结构仍然是同一套 warm editorial 风格

- 文件：[index.css](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/styles/index.css)
- 新增：
  - 章节顺序 badge
  - 术语帮助按钮
  - tooltip 气泡

### 4. 修测试

- 文件：[StandardReportPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/StandardReportPage.test.tsx)
- 锁定：
  - `阅读方法` 不再出现
  - 页面按 `1. 开篇概览`、`2. 决策风向标` 等章节存在
  - `解释：什么是战场` 按钮存在

## 验证

- `cd frontend && npm test -- src/pages/__tests__/StandardReportPage.test.tsx`
  - `2 passed`
- `cd frontend && npm run build`
  - 通过
- 真浏览器验收：
  - `http://127.0.0.1:3006/standard-report/home-cleaning?view=cards`
  - 已确认页面变成 1 到 7 的纵向章节卡片
  - 顶部封面保留
  - `阅读方法` 已去掉
  - `?` tooltip 已生效

## 下一步系统性的计划是什么？

1. 先让用户继续在前端现场点一轮，确认这套标准报告页结构是否就是想要的节奏。
2. 如果确认这套节奏成立，再把真实报告页 `ReportPage.tsx` 收成同一套阅读结构，不再出现“双轨长得不一样”。
3. 页面结构稳定后，再处理内容层的小问题，比如个别机会卡卖点文本过碎。

## 这次执行的价值是什么？

- 这次不是换皮，而是把“页面怎么读”直接变成了“页面自己会说话”。
- 用户现在不需要看额外提示，就能顺着 1 到 7 的结构往下读完整套判断。
