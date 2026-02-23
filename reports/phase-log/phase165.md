# Phase 165 - UI 报告数据展示缺失问题

## 验收场景
- task_id: `0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac`
- 路径: `/report/{task_id}`

## 现象
- 页面能打开且 API 返回 200，但多处展示为空/undefined/占位文案。

## 证据（API 数据存在）
- `/api/report/{task_id}` 返回结构包含：
  - pain_points=15
  - opportunities=7
  - action_items=3
  - competitors=12
  - purchase_drivers 存在
  - report_html 存在

## 根因
- 前端适配层字段映射不一致：
  - UI 使用 `example_posts.title`，但后端提供的是 `example_posts[].content` / `user_examples[]`。
  - UI 用 `action_items.description` 作为驱动力文案，但后端 action_items 里无该字段（有 `problem_definition`/`product_fit`）。
  - 社区名已含 `r/`，UI 又拼一次，导致 `r/r/...`。
  - UI 未使用 `report.purchase_drivers` 与 `report.market_health` 等现成字段。

## 待修复方向（前端）
- 适配层对齐字段名（example_posts.content / user_examples）。
- 驱动力改用 `report.purchase_drivers` 或基于 action_items 的有效字段。
- 社区名展示去重 `r/` 前缀。
- 如需完整报告输出：新增 report_html 渲染区或“完整报告”视图。
