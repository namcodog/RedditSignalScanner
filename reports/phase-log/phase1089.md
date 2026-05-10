# phase1089

- 这轮达到的目的：把泛社区 `hot_floor` 规则补进 Phase 1 dry-run，不让 cap 误伤必须覆盖的最热信号。
- 当前状态变化：`phase1-dry-run.json / md` 已重新生成，泛社区常规学习 cap 为 `25%`，`30%` 以上需人工确认。
- 验收结果：`27` 个泛社区全部带 `hot_floor.must_cover_platform_hot_signal=true`，cap 绕过原因固定为 `must_have_hot_signal`。
- 还没完成什么：这仍是 dry-run 合同，没有真实写 DB，也没有实现线上推荐排序。
- 下一步做什么：人工审核 `69` 个拟新增社区、`27` 个泛社区 cap 和 hot-floor 合同；真实写库另起计划。
