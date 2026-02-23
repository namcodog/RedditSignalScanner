# Phase 19 - 冻结后端黄金路径（/api）第二步：旧路调用可观测 + 监控面板落地 + 样本不足不炸库

日期：2025-12-16  
代码基线：`main@fbc5a89`（工作区 dirty；本阶段以当前代码实况为准）

## 一句话结论

把“旧路（legacy）到底还有没有人用、用了多少”这件事落到**可量化指标**：新增 HTTP 路由调用计数中间件（默认关闭、开关一键开），并把 golden/legacy 的最近 1 分钟调用数写进 `dashboard:performance`；同时修掉一个会让“样本不足”分支写入 DB 直接触发校验失败的坑，避免黄金主线在数据少时“跑着跑着就崩”。

---

## 我查到的证据（以代码为准）

- 黄金/旧路同时挂在 `/api` 下：`backend/app/main.py:create_application`
  - golden：`app.include_router(v1_api_router, prefix="/api")`
  - legacy：`legacy_router = APIRouter(prefix="/api")` + `include_router(...)`
- “旧路调用计数”落点（中间件 + Redis 分桶）：`backend/app/middleware/route_metrics.py:RouteMetricsMiddleware`
- 路由计数 Redis 注入（仅开关开启时）：`backend/app/main.py:create_application`（`app.state.route_metrics_redis = Redis.from_url(...)`）
- 监控面板写入点：`backend/app/tasks/monitoring_task.py:update_performance_dashboard`
- DB 写入质量闸门（sources schema check）：`backend/alembic/versions/20251010_000001_initial_schema.py:validate_sources_schema`
- 样本不足分支来源：`backend/app/services/analysis_engine.py:run_analysis` → `_build_insufficient_sample_result`

---

## 端到端链路图（本期涉及段）

调用方 → FastAPI 路由匹配 → `RouteMetricsMiddleware`（可选计数） → handler（golden/legacy） →（后续 Celery/DB 不改）  
以及：Celery `update_performance_dashboard` → 读 `metrics:route_calls:*` → 写 `dashboard:performance`

---

## 当前问题与根因（按模块归因）

- 门牌/路由层：
  - 问题：`/api/diag/runtime` 曾在 `main.py` 重复定义，和 `diagnostics_router` 冲突（谁先匹配就变成“看运气”），并且会破坏现有测试契约。
  - 根因：把“临时 alias”写进了主路由，造成同一路径多实现共存。
- 可观测性层：
  - 问题：无法量化“旧路（legacy）到底有没有调用”，导致“观察期”没数据抓手。
  - 根因：缺少统一的 HTTP 路由计数，监控面板也没输出 golden/legacy 指标。
- DB/质量闸门层：
  - 问题：样本不足时 `Analysis.sources` 缺少 DB 校验要求的必备字段，写库会被 `validate_sources_schema` 拦下，导致任务失败/重试，主线不稳定。
  - 根因：`_build_insufficient_sample_result` 的 sources 只写了提示信息，没满足 schema gate（communities/posts_analyzed/cache_hit_rate）。

---

## 方案（保守版 / 升级版）

- 保守版（本期已落地）：只加“安检门”和“计数器”，不动核心业务逻辑
  - 路由冲突用契约测试锁死，防止回归
  - HTTP 路由计数默认关闭（env 开关），Redis 写入 best-effort
  - 监控面板输出 golden/legacy 最近 1 分钟调用量 + top legacy paths
  - 样本不足分支补齐 sources 必备字段，保证写库不炸
- 升级版（后续再做）：把 legacy 路由逐个迁到 v1 目录并做下线观察期
  - 迁移后 legacy_calls 应长期趋近 0，再执行清理

---

## 风险与回滚

- 风险：启用路由计数后会多一次 Redis 写操作（轻微开销）；Redis 不可用时我们选择“吞掉异常不影响请求”，但会丢指标。
- 回滚：
  - 不改代码即可回滚：设置 `ENABLE_ROUTE_METRICS=0`（或不设置）即完全关闭计数。
  - Redis 连接可配置：`ROUTE_METRICS_REDIS_URL`（未设置则复用 `Settings.reddit_cache_redis_url`）。
  - 如需彻底移除：删除 `backend/app/middleware/route_metrics.py` 并移除 `backend/app/main.py` 的 `add_middleware`。

---

## 测试与监控（必须包含）

- 新增/强化测试
  - 门牌契约防冲突：`backend/tests/api/test_golden_path_contract.py::test_no_duplicate_routes_for_frozen_contract_paths`
  - 路由计数中间件：`backend/tests/api/test_route_metrics.py`
  - 监控面板写入：`backend/tests/tasks/test_monitoring_task.py::test_update_performance_dashboard`
  - 样本不足 sources schema：`backend/tests/services/test_analysis_engine.py::test_run_analysis_returns_notice_on_sample_shortfall`
- 监控落地（Redis 指标）
  - 路由计数分桶 key：`metrics:route_calls:<minute_bucket>`
  - 面板 key：`dashboard:performance`
  - 新字段：`golden_calls_last_minute`、`legacy_calls_last_minute`、`legacy_top_paths_last_minute`

本地验证（不重置 DB）：
- `SKIP_DB_RESET=1 pytest -q backend/tests/api/test_golden_path_contract.py backend/tests/api/test_route_metrics.py backend/tests/tasks/test_monitoring_task.py backend/tests/services/test_analysis_engine.py::test_run_analysis_returns_notice_on_sample_shortfall`

---

## 验收标准（可量化）

1) 契约：`GET /api/diag/runtime` 不允许出现“同一路径多实现”冲突（测试必须通过）。  
2) 可观测：开启 `ENABLE_ROUTE_METRICS=1` 后（必要时设置 `ROUTE_METRICS_REDIS_URL`），访问 golden/legacy 路由会在 Redis 中产生计数分桶；`update_performance_dashboard` 会把最近 1 分钟的 golden/legacy 调用数写进 `dashboard:performance`。  
3) 稳定性：样本不足时，分析任务不应因 `sources` schema gate 写库失败而进入失败/重试（至少 sources 必备字段齐全且类型正确）。  
