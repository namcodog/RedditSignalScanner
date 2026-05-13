# phase1053

## 这轮达到的目的

修正小程序首页排序，让同日 `breakdown` 不再被 hot/signal 挤出首屏。

## 当前状态变化

- `mini_snapshot` 同日混排候选池已扩大到完整同日卡。
- 新增回归测试覆盖同日 breakdown 发布时间较早的场景。
- 最新快照 `release-b5842b3ee9a8`，front30 为 `hot 15 / signal 14 / breakdown 1`。

## 还没完成什么

- Day5 final gate 仍剩 `3` 个 item。
- trend 当前为 `watching`，仍未 stable。

## 下一步做什么

继续处理剩余 gate item；不为 stable 硬发弱卡。
