# phase1096

## 这轮达到的目的

按用户确认的“每日 25 张”为硬需求，完成 2026-05-08 Hotpost 正式发卡。

## 当前状态变化

- 已发布 25 张：AI 6 / 商业增长 9 / 电商卖家 10，结构为 hot 7 / signal 18。
- 最新小程序快照为 `release-cf603c02169b`，总卡数 725。
- 首页排序已修正为第 1、2 张优先展示 `hot`，且当天 25 张新卡仍整体排在旧卡前面。
- snapshot / miniRelease / miniFavorites / cloud_db / 小程序 snapshot data 校验通过。

## 还没完成什么

- `trend audit` 仍是 `watching`，`remaining_new_releases=5`，不能视为 stable。
- 礼品边界稿已剔除但仍留在 draft 区，后续可按队列治理清理。

## 下一步做什么

用户导入 cloud_db 两个 Upsert 文件后，线上首页应看到前两张为 `hot`，且 2026-05-08 的 25 张新卡排在 2026-05-07 之前。
