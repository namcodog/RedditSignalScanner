# phase859

## 这轮达到的目的

先把拖了两天的出卡问题收口：今天已发布 2 张 `hot` 卡，并把小程序 snapshot 同步链从旧 release 拉回到最新 release。

## 当前状态变化

`card-cand-business-growth-ops-1sm84cm-validate` 和 `card-cand-business-growth-ops-1smshao-validate` 已进入正式 release；`push_mini_snapshot.py` 默认不再在线刷新 `hot controversy`，最新 `mini snapshot` 前两张已经是这两张新卡。

## 还没完成什么

微信侧还没完成 cloud_db 导入、`miniRelease` 重部署和生产预览包重打；下一批 freshness gate 仍未回到 `publish`，当前还是 `hot_inventory_not_fresh_enough`。

## 下一步做什么

先做微信侧同步，让手机端看到今天的新卡；然后再跑一轮 `daily_collect` 补 fresh `hot`，等 gate 回到 `publish` 后继续下一轮出卡。
