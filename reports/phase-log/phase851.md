# phase851

- 这轮达到的目的：把 `docs/sop/` 的操作文档与当前正式口径对齐，清掉旧硬模板残留。
- 当前状态变化：评审与稳态运营 SOP 已改成“先过硬门槛，再按 value-threshold publishing 判断”；freshness gate 明确为 workflow；quota-aware crawl 明确为 rollout target；默认 scope 解释已锁为当前活跃 slice。
- 还没完成什么：quota-aware crawl 和 freshness workflow 还没完全压成项目侧默认生产能力。
- 下一步做什么：继续把夜间 freshest inventory 生产能力和发卡前 freshness workflow 压成默认动作，并按新 phase-log 规则维护文档。
