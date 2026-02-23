# Phase 63 - 全局抓取参数提速（安全峰值）

时间：2025-12-22

## 目标
- 回填完成后，将全局抓取参数稳定提升到安全峰值

## 前提确认
- backfill_queue/compensation_queue 已清零

## 变更内容
- backend/.env:
  - REDDIT_RATE_LIMIT=58
  - REDDIT_RATE_LIMIT_WINDOW_SECONDS=60
  - REDDIT_MAX_CONCURRENCY=3
  - CRAWLER_PATROL_BUCKET_SHARE=0.2

## 运行态操作
- 重启 backfill worker 以加载新配置
  - 新 worker PID: 9337 (concurrency=2)
  - 新 worker PID: 9394 (concurrency=1)
  - 日志：logs/bulk_worker_backfill_20251222-*.log

## 备注
- 当前参数为“理论峰值的安全值”（58/min + 全局桶 + 降突发并发）。
