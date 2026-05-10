# Phase 1083 - Hotpost signal freshness gate 修复

1. 这轮达到的目的
- 修掉 `signal_target_window_underfilled` 的根因：发布面会优先用 72h 内 signal 替换老 signal。

2. 当前状态变化
- `offline_publish_plan` 新增 signal freshness repair pass；不放宽 `signal=72h` 门槛。
- no-collect gate 已从 `rewrite / publish_ready=false` 变为 `publish / publish_ready=true`。

3. 还没完成什么
- topic-tree governance 仍有 `rewrite` 提醒；这不是 freshness gate 阻塞。
- 还没进入 seed / publish 今天新卡。

4. 下一步做什么
- 用当前可发布面进入人工候选确认，再按 V13 seed / review / publish。
