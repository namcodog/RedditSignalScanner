# phase1043

## 这轮达到的目的

修掉小程序首页首屏被 `hot` 连续占满的问题。

## 当前状态变化

根因确认：mini snapshot 先把同一天新发布卡片整体前置；`2026-04-29` 新发布的 11 张全是 `hot`，导致首页前 12 张几乎全是 `hot`。现在已在快照排序里增加单一 lane 打散逻辑，首页首 30 张会混入 `signal / breakdown`。

## 还没完成什么

微信云数据库仍需按最新导入文件手动导入：`mini_release_meta` 和 `mini_release_cards`。

## 下一步做什么

导入 `backend/data/hotpost/mini_snapshots/cloud_db/*.wechat-import.json` 后，在小程序首页确认首屏不再被 `hot` 霸屏。
