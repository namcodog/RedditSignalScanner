# Phase 62 - 评论回填闭环修复与重跑

时间：2025-12-22

## 目标
- 修复 backfill_comments 在 internal post_id 场景的执行问题
- 重新跑 30 天评论回填（run_id=0fd35011-92e5-4c5b-a3ba-2f1773f7c1ae）并验证入库

## 变更摘要
- 修复：backfill_comments 执行前，若 target_value 为数字，尝试按 posts_raw.id 解析为 source_post_id。
- 测试：新增执行器单测覆盖 internal post_id -> source_post_id 映射。

## 代码/测试
- 修改：backend/app/services/crawl/execute_plan.py
- 新增测试：backend/tests/services/test_backfill_comments_executor.py
- 运行测试：pytest backend/tests/services/test_backfill_comments_executor.py -v

## 运行态操作
- 停止旧 backfill worker（PID 69839），重启新 worker（PID 75117）
  - 新日志：logs/bulk_worker_backfill_20251222-165841.log
- 重新设置 run_id=0fd35011-92e5-4c5b-a3ba-2f1773f7c1ae 的 backfill_comments targets 为 queued
- 重新入队 backfill_comments 2720 条（批量入队）
- 修复后重跑：日志显示 processed > 0（已开始真实写入）

## 当前进度快照（17:02 左右）
- backfill_queue（DB1）≈ 2662
- crawler_run_targets：queued 大量消化中
- comments 写入量：crawl_run_id=0fd35011-92e5-4c5b-a3ba-2f1773f7c1ae 当前 1439

## 验证
- DB 验证：comments 表按 crawl_run_id 计数已 > 0
- DevTools：Chrome DevTools MCP 无法连接（已有实例占用），已记录

## 风险/注意事项
- Reddit API 可能出现 403/timeout，compensation_queue 会自动补偿（当前为 0）
- 继续观察 backfill_queue 消化速度与入库增长
