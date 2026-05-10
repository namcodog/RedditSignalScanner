# phase949

1. 这轮达到的目的
- 按 `2026-04-21` 运营决定，把这轮 `40` 个独立题材全部过门禁并正式发布，不再只停在 draft 池。

2. 当前状态变化
- 已正式发布 `40` 张唯一题材卡；对应 draft 已全部从工作区移出，并全部落进 `release-50f4c26a18d3/cards/`。
- 其中 `12` 张 `hot` 已在发布时补齐争议图；`1sktgoh / 1soamj0` 因外部网络抖动重试后通过，其余一次过。
- 最新 mini snapshot 已刷新到 `release-28f7e52ecfa7`，`card_count=72`，`check_mini_release_sync.py` 通过。

3. 还没完成什么
- 设备端如果要看到这版新卡，还要重新导入最新 `mini_release_meta/cards.wechat-import.json`。
- 展示层仍按当前 `release surface` 和 `feed contract` 控制，不等于 40 张都会直接顶到首页前排。

4. 下一步做什么
- 如果要继续今天的运营动作，下一步不是再补今天，而是转去 `22号` 深挖新卡。
- 如果要让真机看到这版，直接导入最新 cloud db 两份文件。
