# phase1007

1. 这轮达到的目的
- 审计 2026-04-24 出卡池和 Reddit / SociaVault 后备链路，接回日常运营节奏。

2. 当前状态变化
- 确认 SociaVault 后备开关和 key 都已启用；修掉评论补采外层 `12s` 批超时，让后备评论请求有 `Reddit 8s + SociaVault 20s + 4s` 完成窗口。
- 新增候选采集测试；候选采集 28 项、Reddit/SociaVault fallback 9 项通过；live 强制低额度验证 SociaVault comments 可返回 `3` 条。
- 重新跑 all-scope safe gate 到 `yield_exhaustion`：discover assist 出现 `2` 次，但评论 fallback 这轮未被触发；final 仍是 `rewrite`。

3. 还没完成什么
- 今天暂不能发布：`signal_target_window_underfilled` 仍在，15 张计划里 fresh signal 只有 `2` 张，且有 `2` 张 stale signal。
- `offline_publish_plan.py` 仍有 unawaited coroutine warning，需要单独修掉后再进发布链。

4. 下一步做什么
- 停止盲跑 all-scope；改为定向补 fresh signal，优先 `business funnel / organic` 和 `ecommerce selection`，够 fresh signal 后再跑 gate。
