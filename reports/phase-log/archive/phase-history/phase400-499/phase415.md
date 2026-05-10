# Phase 415 - 8 条核心路径体验地图固化（2026-03-19）

## 目标
- 完成 Phase 24 最后一项：把 `Input -> Progress -> Report/Hotpost/Admin` 的 8 条核心路径做成正式体验地图与验收基线。

## 体验地图（v1）

| 路径 | 用户当前目标 | 页面主结论 | 下一步动作 | 失败兜底 | 验证证据 |
|---|---|---|---|---|---|
| 1. 首次输入成功出 A 级报告 | 快速判断值不值得继续做 | Report 首屏直接给拍板结论与证据 | 看完整报告 / 逐维探索 | 回输入页重跑（保留描述） | `user-journey.e2e` + `ReportPage.test` |
| 2. 首次输入只出弱结果 | 先定追不追，不硬拍板 | Report 首屏明确“先定值不值得追” | 放大范围再跑 / 逐维探索 | 回输入页并带回方向 | `ReportPage.test`（弱结果） |
| 3. warmup / auto rerun | 理解为何未直接跳报告 | Progress 明确阶段、卡点原因、下一步、预计重试 | 先看当前结果 / 继续等补量 / 回输入页重跑 | 不再盲等，明确可回退 | `ProgressPage.test`（warmup） |
| 4. report 返回输入页重跑 | 不丢原方向地快速迭代 | Input 顶部显示“已带回这次分析方向/待优化方向” | 直接改描述重跑 | 无需手抄内容 | `ReportPage.test` + `InputPage.test` |
| 5. hotpost 快扫后继续深挖 | 从快扫升级到正式分析 | Hotpost 首屏先定追不追 | 继续深挖（带回输入页） | 若失败可回搜索页重扫 | `HotPostResultPage.surface.test` + `product-polish-smoke.e2e` |
| 6. hotpost 快扫后回搜索页重扫 | 在原关键词上快速重扫 | Hotpost 明确可重扫路径 | 回搜索页重扫（带回 query+mode） | 方向不足时不强推深挖 | `HotPostResultPage.surface.test` |
| 7. admin 判断当天系统是否可用 | 先判断今天能不能放心开工 | Admin 首屏给系统状态/建议动作 | 看任务账本 / 看社区池 | 异常时先排查再开新任务 | `admin-dashboard.e2e` + `AdminDashboardPage.test` |
| 8. 权限不足/数据不足/失败态兜底 | 出错时知道该怎么走 | 各页错误态统一成“发生什么 + 下一步” | 重新加载 / 回输入页重跑 / 回搜索页重扫 | 不暴露后台报错细节 | `report-page-simple.e2e` + 页面错误态单测 |

## 当前实现状态
- 路径结构：8/8 已有明确页面承载与动作链。
- 自动化证据：
  - `make test-e2e`：`21 passed`
  - `Input/Progress/Report/Hotpost` 定向页面测试：通过
- 当前缺口：
  - 地图虽然固化完成，但还没做“路径级可视化看板”（后续可做一页 QA checklist 面板）。

## 结论
- `Phase 24` 可判定完成。
- 下一步进入 `Phase 25`：继续收 Admin 的“信任面表达”和系统反馈优先级，让“能不能放心开工”更直观。
