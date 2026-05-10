# phase932

1. 这轮达到的目的
- 把今天确认过的主发池正式发布，并把最新小程序 snapshot / cloud_db 导入包同步出来。

2. 当前状态变化
- 今天新发布 `12` 张卡，正式发布总量从 `315` 增到 `327`。
- 最新小程序快照已更新到 `release-e5b7de02cdb2`，当前 `card_count=66`，其中 `main=54`、`supplement=12`。
- `check_mini_release_sync.py` 已通过，今天这批主发卡都已进入最新 mini snapshot，`hot` 卡争议图也通过 guard。

3. 还没完成什么
- 真机云端是否立刻可见，还差微信开发者工具里的云数据库导入；这一步不是仓内脚本自动完成的。

4. 下一步做什么
- 在微信开发者工具里导入 `mini_release_meta.wechat-import.json` 和 `mini_release_cards.wechat-import.json`，然后真机确认首页首卡已切到当前 release。
