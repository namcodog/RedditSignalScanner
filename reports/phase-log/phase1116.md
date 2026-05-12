# phase1116

## 这轮达到的目的

- 完成 2026-05-11 Hotpost 日常出卡：新增发布 `25` 张，最新快照 `release-8617f1d6f8a6`，总卡数 `822`。

## 当前状态变化

- `signal / hot` 出卡 prompt 已加入“必须提炼证据支撑的隐性信号”规则，避免只复述表层热度。
- 小程序快照、cloud_db、`miniRelease / miniFavorites` 同步检查通过；首页 feed contract 为 `30/30`。

## 还没完成什么

- `trend audit` 仍是 `rebound`，`remaining_new_releases=5`；不能写成 stable。
- 个别候选因 LLM JSON、弱证据、重复发布或语义护栏未发。

## 下一步做什么

- 线上导入本轮 cloud_db 文件时继续用 Upsert；下一轮仍按 `7d fresh + 探索社区隔离报告` 推进。
