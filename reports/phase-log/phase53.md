# Phase 53 - Probe 收尾：probe_hot 12h 定时（Phase2 关）+ probe 完成后自动触发 evaluator（带开关，默认关）

## Key 拍板范围
- `probe_hot`：每 12 小时跑一次
- `r/all rising/top(day)`（Phase 2）：先不启用
- `probe` 执行完立刻触发 evaluator：必须加开关，默认关闭

## 这次落地了什么
### 1) probe 执行完自动触发 evaluator（可开关，默认关闭）
- 新增开关：`PROBE_AUTO_EVALUATE_ENABLED=1`
- 行为：当 `tasks.crawler.execute_target(target_id)` 执行的 `plan_kind=probe` 结束（`completed/partial`）且确实写入了候选社区（`discovered_communities_upserted>0`）时：
  - best-effort 触发：`tasks.discovery.run_community_evaluation`（走 `probe_queue`）
- 默认：关闭（避免一上线就把 evaluator 跑爆）

### 2) probe_hot 定时（每 12 小时一次，默认关闭）
- 开关：`PROBE_HOT_BEAT_ENABLED=1`
- Beat 条目：`probe-hot-12h`（03:15 / 15:15）
- Phase2 热源继续留在配置里，但默认不启用（`PROBE_HOT_SOURCES_PHASE=phase1`）

### 3) 热源列表可配置（不改代码就能换）
- 配置文件：`backend/config/probe_hot_sources.yaml`
- 环境变量：
  - `PROBE_HOT_SOURCES_FILE=config/probe_hot_sources.yaml`
  - `PROBE_HOT_SOURCES_PHASE=phase1`

## 关键文件
- 自动触发 evaluator：`backend/app/tasks/crawl_execute_task.py:1`
- Beat 调度：`backend/app/core/celery_app.py:1`
- probe_hot sources：`backend/config/probe_hot_sources.yaml:1`
- probe planner：`backend/app/tasks/probe_task.py:1`
- SOP：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:310`
- 环境变量示例：`backend/.env.example:1`

## 测试证据
- `pytest -q backend/tests/tasks/test_execute_target_task.py`
- `pytest -q backend/tests/tasks/test_celery_beat_schedule.py`

## 运行建议（最小命令）
- 只跑隔离 worker（推荐本地/生产都用这个口径）：
  - `make start-workers-isolated`
- 开 probe 自动评估（先小流量观察再开）：
  - `export PROBE_AUTO_EVALUATE_ENABLED=1`
- 开 probe_hot 12h 定时（Phase2 继续关着）：
  - `export PROBE_HOT_BEAT_ENABLED=1`
  - `export PROBE_HOT_SOURCES_PHASE=phase1`

