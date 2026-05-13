# Phase 47 - 巡航（patrol）双层护栏：Planner 硬上限 + Executor 兜底（timeout/partial）

## 目标
- 把“巡航队列被大社区/配置失误吃穿”的风险降下来：**planner 先限量**，**executor 再兜底**。
- 口径对齐到 Key 拍板：巡航只负责新鲜（小量、频繁），不做深回填。

## 这次做了什么
### 1) Planner 侧硬上限（写死）
- `plan_kind=patrol` 下单时强制夹住：
  - `posts_limit`：默认 80，最大 100（支持 env：`PATROL_POST_LIMIT` / `PATROL_MAX_POST_LIMIT`）
  - `time_filter`：只允许 `hour/day`（默认 day，禁止 week/month/year/all 这种宽窗口）
  - `patrol_comments_enabled=false`（巡航默认不做评论回填）
- “总量截断”：同一轮心跳最多下单 `EFFECTIVE_BATCH_SIZE` 个 target（避免一次塞爆队列）。

### 2) Executor 侧二次保险（写死）
- `execute_crawl_plan()` 对巡航再次 clamp：
  - `posts_limit` 强制落到 1..100
  - `time_filter` 强制落到 hour/day（其他一律降级为 day）
- `execute_target()` 增加巡航 target 的时间预算：
  - 默认 `PATROL_TARGET_TIME_BUDGET_SECONDS=120`
  - 超时：把该 target 标记为 `partial`（`error_code=timeout`），不当成 failed 自动重跑
- 幂等护栏：`status in {completed, partial}` 的 target 再触发会直接 `skipped`。

## 关键文件
- 巡航 planner：`backend/app/tasks/crawler_task.py:568`
- 执行器兜底（limit/time_filter clamp）：`backend/app/services/crawl/execute_plan.py:12`
- 统一执行入口（timeout/partial/skip）：`backend/app/tasks/crawl_execute_task.py:1`
- target 状态写入：`backend/app/services/crawler_run_targets_service.py:14`
- SOP 更新：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:75`

## 测试证据
- 已跑通过：
  - `pytest -q backend/tests/tasks/test_patrol_planner_task.py backend/tests/tasks/test_execute_target_task.py backend/tests/services/test_execute_crawl_plan_guardrails.py`

## 已知噪音（不阻塞）
- 自适应排序（`AdaptiveScheduler.rank`）在测试库会因为 `posts_raw.value_score` 列缺失打 ERROR log，但已被 try/except 吞掉，不影响本次验收。

## 下一步
- 如果要补齐“partial 自动生成补偿 plan”，建议新增 `compensation` planner（低优先级、延迟执行），只补缺口，不重跑整张 target。
