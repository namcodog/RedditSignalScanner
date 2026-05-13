# Phase 544 - 小程序 trending 详情页价值增强

## 时间
- 2026-03-28

## 背景
- `phase543` 已把小程序 `热点追踪` 链路接成真实业务流：
  - 首页发起搜索
  - 过程页展示真实 `queued / processing`
  - 详情页读取真实 `/api/v1/hotpost/result/{query_id}`
- 但详情页仍偏“字段页”，还没有把 `trending` 的价值真正讲出来。

## 本轮动作

### 1. 扩详情页信息结构，但不改原有风格
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/sections.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/link-actions.tsx`
- 补齐：
  - `03 / 信号分布`
  - `04 / 代表帖子`
  - `05 / 归档证据`
  - `06 / 下一步`

### 2. 接出后端已存在但前端未消费的字段
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`
- 新接字段：
  - `community_distribution`
  - `sentiment_overview`
  - `next_steps`

### 3. 给代表帖子和证据补“查看原帖 / 复制链接”
- 新增：
  - `hotpost-mini/hotpost-mini-app/src/pages/link/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/link/index.config.ts`
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/app.config.ts`
- 产品动作固定为：
  - `查看原帖`
  - `复制链接`

### 4. 收小文件边界，避免继续堆肥
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.scss`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail.scss`
- 关键文件体量：
  - `velocity/index.tsx = 171`
  - `velocity/index.scss = 196`
  - `velocity/detail.scss = 147`
  - `velocity/sections.tsx = 132`
  - `velocity/link-actions.tsx = 23`
  - `services/hotpost.ts = 161`

## 验证
- 执行：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
- 结果：
  - `Compiled successfully`

## 结论
- 小程序 `trending` 详情页已经从“真数据字段页”升级成“可读、可验证、可继续跟踪的分析页”。
- 页面现在不仅能展示：
  - 核心纪要
  - 热度指数
- 还补上了：
  - 为什么现在值得看
  - 信号集中在哪
  - 代表帖子
  - 下一步跟踪什么
  - 查看原帖 / 复制链接

## 下一步
1. 在微信开发者工具里做一轮真实验收，确认 `webview + copy link` 体验。
2. 如果体验稳定，再按同样口径收 `rant / opportunity` 详情页。
