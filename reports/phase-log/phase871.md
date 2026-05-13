# phase871

1. 这轮达到的目的
把产品默认范围正式从临时单 slice 切成 `all-scope`，并验证默认入口不带 `--scope` 时已按全树工作。

2. 当前状态变化
`daily_collect`、`run_offline_publish_plan`、`run_intake_freshness_gate`、`audit_topic_tree_governance` 默认都已不再带 `business-growth-ops`；SOP 和 Makefile 也同步成“产品默认 = all-scope，单 slice 只用于局部修复”。

3. 还没完成什么
当前全树 gate 还没过；真实 `run_intake_freshness_gate --no-collect --no-named-topics` 结果是 `fail(stale_ratio_out_of_control)`，说明范围切对了，但 freshness 还要继续补。

4. 下一步做什么
后续默认都按全树跑 `collect -> plan -> gate`；先收掉当前全树 freshness 问题，等 gate 回到 `publish` 后再继续按 `publish-until-exhausted` 发卡。
