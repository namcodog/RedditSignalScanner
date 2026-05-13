# phase1094 - CI-R2-R5 后端验收版

这轮目的：按用户要求一次性完成 R2-R5，让社区推荐从只读预览推进到后端可验收结果。

当前状态变化：新增独立执行计划 `docs/superpowers/plans/2026-05-08-community-recommendation-r2-r5-execution-plan.md`。推荐服务已补 `15D` 活跃探测合同、语义证据摘要、长尾优先 / 泛社区限额、后端验收摘要。CLI 重新生成 `reports/community-recommendation/preview.md` / `.json`。

验收结果：真实跑数 `acceptance_passed=true / ready_count=30 / tags=3 / recommendations=30`，目标测试 `9 passed`。

边界：当前 `ready` 主要来自 Hotpost 近期探测，不代表 Dev `posts_hot` 已恢复完整 15D 新鲜数据；语义证据主要来自 `community_pool_semantic_profile`，深层 `semantic_observation / semantic_terms` 后续仍可补强。

下一步：用户验收推荐质量；通过后再决定是否进入 API / 前端，不提前做界面。
