# Phase 20 - Spec017 Phase0 清单：黄金路径 & legacy 归档（代码证据版）

日期：2025-12-16  
代码基线：`main@fbc5a89`（工作区 dirty；本清单以当前代码实况为准）

> 说明：你说“旧文档不可信”，所以这里所有条目都只认代码证据（路径 + 符号名）。

---

## 黄金路径清单（入口 / 任务名 / 表 / 配置）

### 1) API 入口（固定门牌：`/api`）

- `POST /api/analyze`
  - handler：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`
  - 鉴权：`decode_jwt_token`
  - DB：写 `tasks`（`app.models.task:Task`）
  - 任务派发：
    - 默认：Celery `tasks.analysis.run`（`backend/app/tasks/analysis_task.py:run_analysis_task`）
    - dev/test 可走 inline：`backend/app/api/v1/endpoints/analyze.py:_schedule_analysis` → `backend/app/tasks/analysis_task.py:execute_analysis_pipeline`

- `GET /api/status/{task_id}`
  - handler：`backend/app/api/v1/endpoints/tasks.py:get_task_status`
  - 鉴权：`decode_jwt_token`
  - DB：读 `tasks`（校验归属）
  - Redis：读 `task-status:{task_id}`（`backend/app/services/task_status_cache.py:TaskStatusCache.get_status`，缓存优先，必要时回源 DB）

- `GET /api/analyze/stream/{task_id}`（SSE）
  - handler：`backend/app/api/v1/endpoints/stream.py:stream_task_progress`
  - 鉴权：`decode_jwt_token`
  - DB：读 `tasks`（校验归属）
  - 事件流：复用 legacy 生成器 `backend/app/api/routes/stream.py:_event_generator`（v1 只是换门牌，不换行为）

- `GET /api/report/{task_id}`
  - handler：`backend/app/api/v1/endpoints/reports.py:get_analysis_report`
  - 鉴权：`decode_jwt_token`
  - DB：通过 `backend/app/services/report_service.py:ReportService.get_report` / `backend/app/repositories/report_repository.py:ReportRepository.get_task_with_analysis` 读取任务+分析+报告
  - 备注：与 legacy 共用限流桶（`backend/app/api/routes/reports.py:REPORT_RATE_LIMITER`）

- `POST /api/export/csv`
  - handler：`backend/app/api/v1/endpoints/export.py:export_csv`
  - 鉴权：`decode_jwt_token`
  - DB：由 `backend/app/services/export/csv_exporter.py:CSVExportService.export_to_csv` 拉取任务/分析数据
  - 文件：输出到 `Settings.report_export_dir`（默认 `reports/exports`）

### 2) 后台任务（Celery / Pipeline）

- `tasks.analysis.run`
  - 定义：`backend/app/tasks/analysis_task.py:run_analysis_task`
  - 主流程：`_run_pipeline_with_retry` → `_execute_success_flow` → `backend/app/services/analysis_engine.py:run_analysis`
  - 写库：`backend/app/tasks/analysis_task.py:_store_analysis_results`
    - `analyses`（`app.models.analysis:Analysis`：`insights`/`sources`/`confidence_score`）
    - `reports`（`app.models.report:Report`：`html_content`/`generated_at`）
    - 并且尝试把部分洞察落到 `InsightCard/Evidence`（见 `_store_analysis_results` 内部 import）
  - 状态回传：写 Redis `task-status:{task_id}`（`TaskStatusCache.set_status`）

### 3) 关键数据表（Postgres）

- `tasks`：任务单（创建、归属、状态、错误信息、重试计数）
  - 模型：`backend/app/models/task.py:Task`
- `analyses`：分析结果（结构化洞察 insights + 血缘/来源 sources）
  - 模型：`backend/app/models/analysis.py:Analysis`
  - DB 质量闸门（check constraint）：`validate_sources_schema` / `validate_insights_schema`
    - 定义：`backend/alembic/versions/20251010_000001_initial_schema.py`
- `reports`：报告渲染结果（HTML）
  - 模型：`backend/app/models/report.py:Report`

（补充：分析引擎会读社区池/帖子表等，详见 `backend/app/services/analysis_engine.py:run_analysis` 内部使用的模型与查询。）

### 4) 关键 Redis key（与黄金主线强相关）

- 任务状态缓存：`task-status:{task_id}`
  - 实现：`backend/app/services/task_status_cache.py:TaskStatusCache`
  - 配置：`TASK_STATUS_REDIS_URL`（默认 `redis://localhost:6379/3`），`TASK_STATUS_TTL_SECONDS`

### 5) 关键配置（Settings + Env 开关）

- Settings（入口）：`backend/app/core/config.py:Settings`
  - `sse_base_path`（默认 `/api/analyze/stream`）
  - `estimated_processing_minutes`
  - `reddit_cache_redis_url`（缓存/监控共用的 Redis URL 默认来源）
  - `report_rate_limit_per_minute` / `report_rate_limit_window_seconds`
  - `report_export_dir`
- Env（行为开关）
  - `ENABLE_CELERY_DISPATCH`：是否强制走 Celery（否则 dev/test 可能 inline）
  - `FAST_E2E_REPORT`：dev/test 报告快速通道

---

## legacy 归档清单（可下线候选）

### A) 当前仍在挂载的 legacy 路由（活的，先别删）

> 证据入口：`backend/app/main.py:create_application` 的 `legacy_router.include_router(...)`  
> 路由前缀证据：`backend/app/api/routes/*` / `backend/app/api/admin/*` 的 `router = APIRouter(prefix=...)`

- `/api/auth/*`
  - router：`backend/app/api/routes/auth.py:router`（prefix=`/auth`）
  - 关键 handler：`register_user` / `login_user` / `get_current_user_me`
  - 备注：这是“登录/鉴权”基础能力，属于业务主线配套，不是黄金分析链路，但大概率必须保留。

- `/api/guidance/*`
  - router：`backend/app/api/routes/guidance.py:router`（prefix=`/guidance`）
  - 关键 handler：`get_input_guidance`
  - 备注：输入引导类接口，是否可迁/可下线以路由计数观察期为准。

- `/api/metrics/*`
  - router：`backend/app/api/routes/metrics.py:router`（prefix=`/metrics`）
  - 关键 handler：`get_quality_metrics` / `get_daily_quality_metrics`
  - 备注：质量看板接口，属于观测面，不建议和黄金分析链路绑在一起删。

- `/api/diag/*`
  - router：`backend/app/api/routes/diagnostics.py:router`（prefix=`/diag`）
  - 关键 handler：`get_runtime_diagnostics`（管理员诊断）

- `/api/insights/*`
  - router：`backend/app/api/routes/insights.py:router`（prefix=`/insights`）
  - 关键 handler：`list_insights_by_task` / `get_insight`

- `/api/beta/*`
  - router：`backend/app/api/routes/beta_feedback.py:router`（prefix=`/beta`）
  - 关键 handler：`submit_beta_feedback`

- `/api/admin/*`（后台运营/管理）
  - router：`backend/app/api/routes/admin.py:router`（prefix=`/admin`）
  - 关键 handler：`get_dashboard_stats` / `get_recent_tasks` / `get_active_users`

- `/api/admin/communities/*`（注意：同前缀来自两个 router）
  - router：`backend/app/api/routes/admin_communities.py:router`（prefix=`/admin/communities`）
    - 关键 handler：`get_communities_summary` / `download_template` / `import_communities` / `get_import_history`
  - router：`backend/app/api/routes/admin_community_pool.py:router`（prefix=`/admin/communities`）
    - 关键 handler（节选）：`list_community_pool` / `approve_community` / `reject_community` / `disable_community` / `batch_update_community_pool` / `list_tier_audit_logs`

- `/api/admin/beta/*`
  - router：`backend/app/api/routes/admin_beta_feedback.py:router`（prefix=`/admin/beta`）
  - 关键 handler：`list_beta_feedback`

- `/api/admin/metrics/*`
  - router：`backend/app/api/admin/metrics.py:router`（prefix=`/admin/metrics`）
  - 关键 handler：`get_semantic_metrics`

- `/api/admin/semantic-candidates/*`
  - router：`backend/app/api/admin/semantic_candidates.py:router`（prefix=`/admin/semantic-candidates`）
  - 关键 handler（节选）：`list_semantic_candidates` / `approve_semantic_candidate` / `reject_semantic_candidate`

### B) 代码里还在，但 main.py 没挂载的 legacy 路由（半死：可作为“下线候选池”）

- 已存在但当前未挂载（main.py 未 include）：
  - `backend/app/api/routes/analyze.py`（定义了 `/analyze`）
  - `backend/app/api/routes/tasks.py`（定义了 `/status`、`/tasks`）
  - `backend/app/api/routes/export.py`（定义了 `/export`）
  - `backend/app/api/routes/reports.py`（定义了 `/report`）
  - `backend/app/api/routes/stream.py`（定义了 `/analyze/...` 的 SSE 生成器）

> 重要提醒：虽然 `reports.py` / `stream.py` 没被“路由挂载”，但 **v1 代码仍在复用它们的实现**：  
> - `backend/app/api/v1/endpoints/stream.py` 直接 `import app.api.routes.stream as legacy_stream`  
> - `backend/app/api/v1/endpoints/reports.py` 复用 `app.api.routes.reports` 的限流桶  
> 所以这两块目前不能直接删；正确做法是把“共享逻辑”搬到 `services/` 再逐步解耦。

### C) 下线观察期策略（用数据说话）

- 先开计数（只影响指标，不影响请求）：设置 `ENABLE_ROUTE_METRICS=1`（必要时设置 `ROUTE_METRICS_REDIS_URL`，否则复用 `Settings.reddit_cache_redis_url`）
- 看板看哪里：
  - `dashboard:performance.golden_calls_last_minute`
  - `dashboard:performance.legacy_calls_last_minute`
  - `dashboard:performance.legacy_top_paths_last_minute`
- 下线条件建议（可调整）：
  - 对某条 legacy path：连续观察 N 天（例如 7 天）调用量为 0 → 进入“可删候选”
  - 对“仍有调用”的 legacy path：先决定“迁到 v1 目录”还是“保留为支撑接口”，再定清理节奏
