# phase60 - C组黑名单与验毒队列监控

日期: 2025-12-22

## 执行
- C 组社区在 community_pool 设为 is_blacklisted=true + is_active=false
- C 组在 discovered_communities 标记为 blacklisted
- 将 C 组已排队的验毒 targets 直接标记 completed (reason=blacklisted_c_group)
- 启动 backfill_queue 监控脚本：scripts/watch_backfill_eval.sh

## 当前状态
- 27 社区验毒 targets: queued=105, completed=30 (C组)
- backfill_queue: 135 (包含已完成但尚未被 worker 消费的跳过任务)
- 监控日志: logs/backfill_watch_20251222-160326.log

## 备注
- bulk worker 包含 crawler_queue/monitoring_queue, 可能与回填抢 API 配额

## 下一步
- 等 backfill_queue 与 pending_targets 归零后，脚本自动触发 run_community_evaluation
- 如需提速，可临时收紧 bulk worker 只监听 backfill_queue/compensation_queue
