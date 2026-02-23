# Phase 51 - P1 探针输入端（probe_hot v1）：受控热源 + 双层限额 + evidence/discovered 落库

## 目标（Key 的拍板口径）
把 `probe_hot` 做成“可控雷达”，接进同一条探针闭环，但不把系统搞乱：
- 只产 `evidence_posts` + `discovered_communities`
- 不碰 `community_cache` 水位线
- 不直接触发回填（回填仍只由 evaluator `approved` 触发）
- 热源/限额可配置，但 executor 必须硬夹上限（防灌爆）

## 这次做了什么
### 1) 新增 probe_hot Planner（只下单 + 入队）
- 任务：`tasks.probe.run_hot_probe`
- 默认热源（Phase 1）：8 个战区锚点社区 `hot`
- Planner 侧先 clamp（防手滑）：sources<=20、posts_per_source<=50、candidates<=100、evidence_per_sub<=5、max_age_hours=24..168
- 下单写入 `crawler_run_targets.config`，并 enqueue 到 `probe_queue`，执行仍走统一入口 `tasks.crawler.execute_target(target_id)`

### 2) 执行器支持 probe_hot（meta.source=hot）
- `execute_crawl_plan` 支持 `plan_kind=probe` 的 `meta.source in {search, hot}`
- hot 侧逻辑：多热源合并 → 去重 → 过滤阈值（score/comments/新鲜度/spam）→ 候选社区 TopN → 每社区证据帖 TopM → 超限标记 `partial(caps_reached)`
- 同时保留 search 的口径：证据帖 Top-N 与候选社区 Top-K 解耦（证据是审计资产，不被候选上限“连坐”砍掉）

### 3) 测试补齐
- `probe_hot`：
  - 写 `evidence_posts` + upsert `discovered_communities`
  - 严格限额（候选×每社区证据）
  - 幂等：重复执行不会刷爆 `evidence_posts`

### 4) SOP 补文档（防止口径再分叉）
- 补了 `probe_hot v1` 的两阶段热源、可调旋钮、以及 executor 写死保险丝

## 关键文件
- Planner：`backend/app/tasks/probe_task.py:1`
- 执行器：`backend/app/services/crawl/execute_plan.py:1`
- probe_hot 测试：
  - `backend/tests/services/test_probe_hot_executor.py:1`
  - `backend/tests/tasks/test_probe_hot_planner_task.py:1`
- SOP：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:280`

## 测试证据
- `pytest -q backend/tests/services/test_probe_hot_executor.py backend/tests/tasks/test_probe_hot_planner_task.py`
- `pytest -q backend/tests/services/test_probe_search_executor.py backend/tests/tasks/test_probe_planner_task.py backend/tests/tasks/test_execute_target_task.py`

## 下一步
- （可选）把 `run_hot_probe` 接到 Celery Beat（需要 Key 决定频率/上线策略）
- Phase 2 热源（`r/all rising` + `r/all top(day)`）在 Phase 1 跑稳 3～7 天后再加

