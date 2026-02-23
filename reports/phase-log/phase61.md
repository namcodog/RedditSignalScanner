# phase61 - backfill加速 (安全模式)

日期: 2025-12-22

## 目标
- 让验毒回填优先消化，避免其他任务抢 API 配额

## 执行
- 停止原 bulk worker (包含 monitoring/crawler/maintenance 队列)
- 启动 backfill 专用 bulk worker:
  - queues: backfill_queue, compensation_queue
  - concurrency: 2
  - log: logs/bulk_worker_backfill_20251222-161906.log

## 当前状态快照
- backfill_queue: 133 (持续下降)
- crawler_run_targets: completed=45, partial=3, queued=89, running=1

## 预计耗时
- 以当前速度估算，剩余 90 左右任务预计 15-40 分钟内消化
- 实际以队列消化与 pending_targets 归零为准

## 下一步
- 监控脚本清空后自动触发 run_community_evaluation
- 评估完成后再执行 A 组 12 个月回填
