# Phase 69 - A组12个月评论回填启动（smart_shallow 默认）

时间：2025-12-22

## 目标
- 使用 smart_shallow 默认策略启动 A 组 12 个月评论回填
- 兼顾效率最大化与安全限流

## 前置核查
- 队列：backfill_queue=0, compensation_queue=0（启动前）
- backfill worker 重启：concurrency=2 + 1（仅 backfill/compensation）

## 启动参数（默认）
- mode=smart_shallow, depth=2
- top 30 / reply-top 15 / new 20 / total 50
- 爆帖自动加料：num_comments>=300 或 score>=500 → total 150, depth>=3
- 仅回填 num_comments>0 且 is_current 的帖子

## 执行结果
- 统计 A 组近 12 个月 posts：1624 条（num_comments>0）
- crawl_run_id: 53584ba7-0000-435f-af33-a18aed700082
- 计划入队：1433 条（去重后）
- 当前队列：backfill_queue≈1423（已开始消费）

## 下一步
- 监控 backfill_queue 与 run 目标状态，等待清零
- 如需提速再评估增量 worker 或补偿策略
