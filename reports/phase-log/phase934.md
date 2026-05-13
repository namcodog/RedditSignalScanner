# phase934

1. 这轮达到的目的
- 修正首页排序口径，让同一发布日的新卡先顶到首页前面，并先隐藏 hot 卡前端的天数时间。

2. 当前状态变化
- `mini_snapshot` 已改成按 `published_at` 的发布日优先；当新发卡和旧卡共存时，新发卡会先留在首页主面前段，再对旧卡继续做货架混排。
- 最新 mini snapshot 已重推到 `release-433ac35919ac`，今天 `2026-04-20` 新发的 `12` 张卡现在都在主面前 `12` 位，不再下沉到 `15天补充`。
- 前端已隐藏 hot 卡的 `今天 / X天前` 时间文案；`dist-dev` 和 `dist-prod` 都已重建通过。

3. 还没完成什么
- 真机要看到这次新顺序，还需要重新导入最新的 `mini_release_meta.wechat-import.json` 和 `mini_release_cards.wechat-import.json`。

4. 下一步做什么
- 在微信开发者工具重新导入 cloud db 两个导入包，然后真机确认首页前 `12` 张已切成今天这批新卡。
