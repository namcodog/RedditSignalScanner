# phase857

1. 这轮达到的目的
把 `SociaVault` 开关和 API key 接进 `daily_collect.py` 实际读取的本地 env 源，并完成一次真实 collect 自检。

2. 当前状态变化
`sociavault_enabled = True`、`has_sociavault_api_key = True`；真实 `safe` collect 能正常跑完，没有把 `SociaVault` 误切成主采。

3. 还没完成什么
本轮 Reddit API 运行正常，所以 `fallback_comment_requests / comment_assist_hits / rescue_hits` 仍然是 `0`，还没有真实 assist/rescue 证据。

4. 下一步做什么
继续看 timeout / low quota / 429 场景下，`SociaVault` 是否只在 assist/rescue 位介入。
