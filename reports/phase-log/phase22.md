# Phase 22 - Dual-Mode 落地（保守版）：mode 从 API → DB → 后台执行打通

日期：2025-12-17  
代码基线：`main@fbc5a89`（工作区 dirty；本阶段以当前代码实况为准）

## 一句话结论

把“市场 / 运营”这个开关真正打通了：**调用方在 `/api/analyze` 里传 mode → tasks 表永久记住 → 后台跑任务时按 mode 过滤社区范围**，不再靠系统自己瞎猜。

---

## 我查到的证据（以代码为准）

### 1) API 入口（对外还是 `/api`）
- 路由挂载：`backend/app/main.py:create_application`（v1 router 仍挂在 `prefix="/api"`）
- 创建任务：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`

### 2) mode 入参 + 落库
- 入参 schema：`backend/app/schemas/task.py:TaskCreate.mode`
- tasks 表字段：`backend/app/models/task.py:Task.mode`
- DB 迁移：`backend/alembic/versions/20251217_000001_add_mode_to_tasks.py`

### 3) 后台执行按 mode 生效
- pipeline 读取 mode：`backend/app/tasks/analysis_task.py:_mark_processing`（写入 `TaskSummary.mode`）
- 引擎按 mode 过滤社区：`backend/app/services/analysis_engine.py:_filter_communities_by_mode`
- operations 社区来源：`config/community_roles.yaml`（role=operations 的 communities 列表）

---

## 端到端链路（本期只做保守版）

`POST /api/analyze (mode=...)`  
→ tasks 表写入 `mode`  
→ pipeline 执行时读出 `mode`  
→ analysis_engine 用 `config/community_roles.yaml` 把社区范围“筛到正确的那一边”  

---

## 当前问题与根因（按模块归因）

### 1) 之前 mode 根本传不进去
- 现状：`/api/analyze` 只收 `product_description`，DB 也不存 mode。
- 后果：后台只能“看一句话猜关键词/猜社区”，无法做到你要的“双模式可控、可追溯”。

---

## 方案（保守版 / 升级版）

### 保守版（本期已落地）
- tasks 表加 `mode`（默认 `market_insight`，并限制只能 `market_insight|operations`）
- API 支持传 `mode` 并落库
- pipeline 把 mode 带进分析引擎
- 分析引擎按 mode 过滤社区范围（operations 只看 operations 社区；market_insight 自动排除 operations 社区）

### 升级版（下一期再做）
- 把 facts v2（A/B/C/X 门禁 + TopicProfile）收编成 API 的唯一主入口（而不是脚本主导）

---

## 风险与回滚

- 风险：如果 community_pool 里没收录 enough 的 operations 社区，`mode=operations` 可能会“可用社区=0”，会直接失败（这是“诚实失败”，方便定位数据端缺口）。
- 回滚：不改数据也能回滚——把引擎里的 mode 过滤逻辑关掉/移除即可；DB 的 mode 字段保留不影响旧逻辑。

---

## 测试与监控（必须包含）

### 新增/更新测试
- `backend/tests/api/test_analyze.py`
  - 默认 mode 写入 market_insight
  - 传 operations 能落库
  - 非法 mode 直接 422

### 本地验证命令（我实际跑过）
- `cd backend && PYTEST_RUNNING=1 APP_ENV=test ENABLE_CELERY_DISPATCH=0 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q tests/api/test_analyze.py`

---

## 额外修复（为保证测试库/新库能跑起来）

> 说明：这几处不是“功能加戏”，而是为了让 **alembic 迁移在干净/测试库上不崩**，否则我们连最基本的回归测试都跑不了。

- ✅ scores 表可能不存在时不再炸迁移：`backend/alembic/versions/20251213_000002_enforce_scores_latest_unique.py`
  - `post_scores/comment_scores` 不存在就跳过 dedupe+index（存在则照常执行）
- ✅ posts_raw/comments 缺字段时先补再改默认：`backend/alembic/versions/20251214_000004_add_tracking_fields_posts_comments.py`
  - 例如 `business_pool` 缺失会先 add_column，再设置默认
- ✅ scoring view 缺失时语义视图用“空视图”兜底：`backend/alembic/versions/20251214_000005_create_semantic_task_views.py`
  - `post_scores_latest_v` 不存在时，`v_comment_semantic_tasks` 仍可创建但返回空
- ✅ uuid_generate_v4 不存在时自动装扩展：`backend/alembic/versions/20251215_000001_add_crawler_runs.py`
  - 先 `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`

---

## 验收标准（可量化）

1) 调用 `/api/analyze` 不传 mode：DB 里该任务 `mode=market_insight`。  
2) 调用 `/api/analyze` 传 `mode=operations`：DB 里该任务 `mode=operations`。  
3) 非法 mode（比如 `"auto"`）一律被接口挡住（422），不允许脏数据进库。  
