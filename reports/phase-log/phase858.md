# phase858

## 这轮达到的目的

把 quota-aware rollout 的两个默认入口收口：`daily_collect` 默认只跑 `business-growth-ops`，`run_intake_freshness_gate` 默认改成 `collect -> sync -> plan -> gate`。

## 当前状态变化

`daily_collect` 只有显式传 `--all-scope` 才会全量外扩；`run_intake_freshness_gate` 现在默认先跑 quota-aware collect，再做同步、排卡和 freshness 判断；`Makefile` 已新增 `hotpost-intake-freshness-gate` 统一入口。

## 还没完成什么

`SociaVault` 的“连续 2 轮 dry cycle 且 discover 面未扫完”触发器还没有项目侧显式实现；`dry_cycle` 仍按整体 `publishable_total` 计，不是纯 `discover -> enrich` 收益计数；真实运行里 `assist` 触发还偏少。

## 下一步做什么

继续在 `429 / timeout / low-quota` 场景下验证 `assist + rescue`；再决定是否补 phase-aware backfill offload 和 trigger 4 的显式实现。
