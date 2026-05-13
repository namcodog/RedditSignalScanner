# phase876

1. 这轮达到的目的
把题材树治理从“front30 可见层纠偏”继续前移到 `publish_list` 的 plan-time selection，直接收紧老社区和强 pack 过重。

2. 当前状态变化
新增 `TopicTreePublishSurfacePlanner` 并接进 `offline_publish_plan`；`source_health` 现在会直接影响候选排序。真实 all-scope 验证已跑通，但当前结果仍是 `actual_total = 0`、`yield_exhausted = true`，说明规则已落地，这轮只是没有新的净新增价值。

3. 还没完成什么
最新改善还主要体现在新一轮发布面的形成逻辑，不等于 `250` 张总库存已经健康；`upstream-winds`、`tools-efficiency`、`funnel-conversion`、`category-winds`、`kill-signals` 这些 pack 的长期来源健康还没收干净。

4. 下一步做什么
继续按全树真实 workflow 跑后续发布，重点看新 release 本身是否也开始同步去老社区 / 强 pack 化，而不只是 front30 排序层更均衡。
