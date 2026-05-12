# phase1115

## 这轮达到的目的

- 把用户确认的 Hotpost 探索社区真正写入 Dev `community_pool`，完成 R12。

## 当前状态变化

- 新增 Dev 写入脚本 `backend/scripts/hotpost/community_pool_r12_dev_write.py`，默认 dry-run，只有 `--execute` 才提交。
- 本轮写入 `reddit_signal_scanner_dev`：`r/aeo`、`r/ai_ugc_marketing`、`r/growthhacking`。
- 未删除社区池计数 `356 -> 359`；Gold DB、小程序快照和 cloud DB 未写。
- rollback SQL：`reports/community-governance/community-pool-r12-dev-write-rollback-2026-05-10.sql`；推荐刷新后为 `tags=9 / recommendations=68 / ready_count=33 / acceptance_passed=true`。

## 还没完成什么

- 还没做 API / 前端；后续 R12 写入仍必须逐次人工确认。

## 下一步做什么

- 复核新增社区的推荐质量，再继续用同一 SOP 处理下一批 `pool_candidate`。
