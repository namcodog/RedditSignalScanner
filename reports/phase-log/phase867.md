# phase867

- 这轮达到的目的：把题材树四层治理压进项目侧默认审计，并拆掉旧固定模板在 plan / gate 里的硬 veto。
- 当前状态变化：`offline_publish_plan` 已接入 `topic_tree_governance`；`freshness gate` 不再因固定数量和固定 lane 直接 fail；新增 `make hotpost-topic-tree-audit` 入口。
- 还没完成什么：当前 `business-growth-ops` 的真实审计仍是 `rewrite`，主因是轮换层社区疲劳和 `funnel-conversion` 来源健康不足。
- 下一步做什么：先按审计结果收 `rotation rewrite` 和 `source health rewrite`，再继续下一轮 review / publish。
