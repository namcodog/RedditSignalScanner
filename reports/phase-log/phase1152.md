# phase1152 - 2026-06-08 Reddit 采集路线治理

## 这轮达到的目的
- 核实 2026-06-08 标准出卡入口卡在 Reddit OAuth / TLS 网络层，不是 V13、发布门禁或内容质量问题。

## 当前状态变化
- `RedditAPIClient.authenticate()` 已补 token endpoint 临时连接错误的 2 次短重试和统一 `RedditAPIError` 归类。
- 新增 `make hotpost-reddit-preflight`，标准 `make hotpost-publish-until-exhausted` 会先验证 `oauth_token` 和最小 `hot listing`。
- 日常产卡 SOP 和稳态运营 SOP 已同步：同类 Reddit 连接错误连续 `2` 次后停止盲重试，预检通过后才恢复完整 collect。

## 还没完成什么
- 还没恢复执行 2026-06-07 / 2026-06-08 的正式出卡发布轮；当前只完成路线修复和预检验证。

## 下一步做什么
- 重新跑 `make hotpost-publish-until-exhausted`，继续 6月7日 / 6月8日出卡计划；若预检失败，按网络阻塞记录，不下 no-supply 结论。
