# Phase 64 - A 组 12 个月 posts 回填启动

时间：2025-12-22

## 目标
- 对 A 组 13 个社区启动 12 个月 posts 回填

## 执行参数
- 社区：r/aquariums r/cats r/chatgpt r/localllama r/stablediffusion r/saas r/promptengineering r/dogs r/malelivingspace r/puppy101 r/pets r/battlestations r/askelectronics
- 窗口：12 个月（lookback_days=365）
- 切片：7 天/片
- 单片上限：posts_limit=300

## 运行信息
- crawl_run_id: f6a36768-f25f-4339-9ca7-c6453fadd93f
- 目标数：689（13 * 53 slices）

## 当前进度快照
- backfill_queue（Redis DB1）：671
- crawler_run_targets：completed 37 / partial 1 / running 2 / queued 650

## 备注
- 使用新全局限流参数（58/60 + 并发=3 + 桶分配 0.2）
