# phase937

1. 这轮达到的目的
- 修正“当天新发卡优先”后的首页副作用，不再让 `hot` 一口气占满首页前排。

2. 当前状态变化
- `mini_snapshot` 已补上“同一天新卡内部也要按 lane 混排”的降级逻辑；即使当天新卡里没有 `breakdown`，也不会直接退回成整段 `hot` 顺序。
- 最新 mini snapshot 已更新到 `release-e76716b86a0d`；首页前 `15` 位当前是 `8 hot / 7 signal`，不再是之前那种几乎被 `hot` 整段占满的状态。
- `check_mini_release_sync.py` 已通过；这次新 release 生成后，`trend audit` 当前状态为 `watching`，焦点仍在 `release_surface`。

3. 还没完成什么
- 真机要看到这次新顺序，还需要重新导入最新的 `mini_release_meta.wechat-import.json` 和 `mini_release_cards.wechat-import.json`。

4. 下一步做什么
- 先在微信开发者工具重新导入 cloud db 两个导入包，确认设备端首页前排已从“hot 整段占满”变成 `hot/signal` 混排。
