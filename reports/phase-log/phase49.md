# Phase 49 - P1 探针最小闭环：评估通过 → 自动回填 30 天（固定配额上限）

## 目标（Key 拍板）
把探针/发现链路收成一个最小可用闭环：
`discovered_communities → evaluator → 入池 → 自动 backfill 30 天`

核心要求两条：
1) 自动回填必须走统一执行入口（`execute_target(target_id)`），别再跑脚本直写库  
2) 自动回填必须有固定配额上限（防止把队列/API/DB 跑爆）

## 这次做了什么
### 1) 新增“自动回填 30 天”下单服务
- 新增 `plan_auto_backfill_posts_targets(...)`：
  - 每个社区回填 30 天
  - 默认 7 天切片（30 天≈5片）
  - 每个社区总 posts 预算默认 300，并均分到每个 slice 的 `limits.posts_limit`
  - `meta.budget_cap=true` 标记这是“额度回填”（不是扫干净窗口）

### 2) evaluator 通过后自动下单并入队执行
- `discovery_task._run_community_evaluation()` 在拿到 `approved` 结果后：
  - 创建一个新的 `crawl_run_id`
  - 生成对应的回填 targets（写入 `crawler_run_targets`，status=queued）
  - 把每个 target enqueue 到 `backfill_queue`（执行仍走 `tasks.crawler.execute_target`）

### 3) 防止“额度回填被 partial 补偿越补越大”
- 当 `budget_cap=true` 且 `reason=cursor_remaining` 时：
  - 仍落 target 状态为 `partial`（可审计）
  - **但不再自动生成补偿 targets**（避免把预算穿透）

## 关键文件
- 自动回填下单：`backend/app/services/discovery/auto_backfill_service.py:1`
- 评估通过自动触发：`backend/app/tasks/discovery_task.py:1`
- budget_cap 跳过补偿：`backend/app/tasks/crawl_execute_task.py:449`
- SOP 更新：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:280`

## 测试证据
- 新增/覆盖：
  - `pytest -q backend/tests/services/test_discovery_auto_backfill_service.py`
  - `pytest -q backend/tests/tasks/test_discovery_auto_backfill_task.py`
  - `pytest -q backend/tests/tasks/test_execute_target_task.py`

## 下一步
- P1 的“探针输入端”继续补齐：search/hot 产 `evidence_posts` 并写入 `discovered_communities`（source=search/hot），再复用同一条闭环。

