# phase1097

## 这轮达到的目的

把 Reddit Community Intelligence 社区推荐合同从文档口径推进到后端 preview 实现，重点修掉硬编码标签和用户文案泄露内部证据词。

## 当前状态变化

- `CAPABILITY_SEEDS` 已从 production code 移除。
- 新增 `backend/config/community_interest_tags.json`，承载具像化标签、匹配规则、泛社区名单、分数权重和用户推荐文案模板。
- 当前 preview 生成 `6` 个标签、`55` 条推荐样例，`acceptance_passed=true / ready_count=29`。
- 用户可见 preview 区不再暴露 `Hotpost / community_pool / semantic_observation / semantic ledger / 语义账本`。

## 还没完成什么

- 真实 Reddit 活跃探测和深层 `semantic_observation / semantic_terms` 密度仍需后续补强。
- 具像化标签目录还需要用户验收后继续收紧，避免标签重新变宽。

## 下一步做什么

用户验收 `reports/community-recommendation/preview.md` 和 `preview.json`；验收通过后再决定是否进入 API / 前端。
