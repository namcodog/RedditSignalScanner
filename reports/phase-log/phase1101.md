# phase1101 - Hotpost 社区发现回流规划

## 这轮达到的目的
核实探索社区池实现，并单独规划回流 `community_pool` 链路。

## 当前状态变化
- 探索社区池合同通过验证：默认隔离、显式小配额、只读审计。
- 审计重跑为 `row_count=16`，全部 `keep_testing`，还没有真实产出证据。
- 新增计划：`docs/superpowers/plans/2026-05-08-hotpost-community-pool-feedback-loop-plan.md`。

## 还没完成什么
- 还没有显式探索试采入口。
- 还没有回流 dry-run 报告。

## 下一步做什么
先做 R10 显式探索试采，再做 R11 回流 dry-run；不做前端/API，不自动入池。
