# Phase 52 - probe_hot 可运营化：热源列表配置化 + 可选 Beat 调度（默认关）

## 目标（Key 的“先稳再放开”口径）
- probe_hot 的热源列表必须“好换”：不改代码也能换（配置文件/环境变量）
- probe_hot 可以“接上定时跑”，但默认必须是关闭的（避免一上线就把系统跑爆）
- 继续坚持两层护栏：planner 先 clamp，executor 再 hard clamp

## 这次做了什么
### 1) 热源列表配置化（不改代码也能换）
- 新增配置：`backend/config/probe_hot_sources.yaml`
  - `phase1`：8 个锚点社区（默认）
  - `phase2`：`r/all rising` + `top(day)`（预留，建议跑稳后再开）
- Planner 默认从文件读取：
  - `PROBE_HOT_SOURCES_FILE`（默认 `config/probe_hot_sources.yaml`）
  - `PROBE_HOT_SOURCES_PHASE`（默认 `phase1`）

### 2) 可选 Beat 调度（默认关闭）
- `backend/app/core/celery_app.py` 加入：
  - `task_routes`：`tasks.probe.run_search_probe` / `tasks.probe.run_hot_probe` → `probe_queue`
  - 可选调度：`PROBE_HOT_BEAT_ENABLED=1` 时才会注册 `probe-hot-daily`

## 关键文件
- 配置：`backend/config/probe_hot_sources.yaml:1`
- Planner：`backend/app/tasks/probe_task.py:1`
- Beat & Routes：`backend/app/core/celery_app.py:1`
- SOP：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:325`

## 测试证据
- `pytest -q backend/tests/tasks/test_celery_beat_schedule.py`
- `pytest -q backend/tests/services/test_probe_hot_executor.py backend/tests/tasks/test_probe_hot_planner_task.py`

## 下一步
- Key 拍频率/上线策略后，再决定：
  - `probe-hot-daily` 的执行频率（每天/每几小时）
  - Phase 2 热源什么时候打开（建议 Phase 1 跑稳 3～7 天后）

