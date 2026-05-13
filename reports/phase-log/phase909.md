# phase909

1. 这轮达到的目的
   把审计里暴露出的默认策略硬编码真正拆掉，让补卡和 named-topic 默认策略回到配置驱动，而不是继续停留在报告结论。

2. 当前状态变化
   `named-topic` 的 topic registry / preset / 默认 preset 已从 Python 常量迁到 `backend/config/hotpost_named_topic_watchlists.yaml`；`collect_named_topics.py`、`run_intake_freshness_gate.py` 和 `topic_metadata` 都已接到新配置。`freshness gate` 的 lane target 也不再写死 `15 -> 9/4/2`，而是按 rolling mix 配置缩放；`recommended_actions` 与默认输出路径里的旧 `15` 遗留也已清掉。`runs_per_day` 现已和正式口径对齐为 `3`。

3. 还没完成什么
   这轮收掉的是“默认策略硬编码”，不是把所有运营纪律都自动化；当前每天跑几轮、怎么补薄，仍主要由 SOP 管，不是整夜自动编排器。

4. 下一步做什么
   接下来继续按配置化入口补 `small-goods`，优先走 `selection-30d-small-goods-demand / selection-30d-small-goods-tail`；如果后面还要继续结构化，就把更多 SOP 纪律下沉成 operation contract，而不是再往脚本里塞默认值。
