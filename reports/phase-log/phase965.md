# phase965

1. 这轮达到的目的
- 把小程序展示层从“滚动库存裁剪”改回“全部已发布卡可见”，收掉和产品目标冲突的前台缩水逻辑。

2. 当前状态变化
- `mini_snapshot` 不再按 freshness / supplement 裁掉旧卡；当前 snapshot 会保留全部已发布卡，只在前面的展示窗口里做排序混排。
- 相关测试已改到新口径：验证“全部已发布卡都进 snapshot”，不再默认接受 `main/supplement` 裁剪。
- 项目说明和补充合同已同步，明确 `supplement` 不再决定小程序前台可见性。
- 最新 snapshot 已重推到 `release-927667854aa0`，当前 `card_count = 392`、`main_card_count = 392`、`supplement_card_count = 0`。

3. 还没完成什么
- 真机环境还需要重新导入这次新的 cloud db 文件。

4. 下一步做什么
- 重新导入 `mini_release_meta / mini_release_cards`，让设备端看到这版 `392` 张全量卡池。
