# Phase 29 - Task.audit_level 落地：Gold/Lab/Noise 任务意图可审计（允许显式覆盖）

日期：2025-12-17  
范围：仅后端 + 数据库；不改前端；不改“黄金门牌”（仍冻结 `/api`）；本阶段只把“任务意图”落库，后续再接 facts_v2 分层存储/保留期/validator 分级。

## 一句话结论

以前系统只能“靠猜”（看 `topic_profile_id`、看运行结果）去推断任务属于黄金还是试验，**一旦出现“为什么没留审计包 / 为什么留了这么多”就容易扯皮**。  
本阶段把口径写死到数据库：`tasks.audit_level ∈ {gold, lab, noise}`，创建时按默认规则自动填，但允许显式覆盖，后续所有审计包/保留期/拦截规则都可以稳定挂在这个字段上。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- 任务有没有“审计价值”属于**产品意图**，但以前 DB 里没有字段记住它。
- 结果：系统只能靠 `topic_profile_id` 等信号去猜；遇到争议时没有“铁证”，也没法做分层保留（90/30/7）这类治理动作。

### 2）是否已精确定位？
- 任务表模型：`backend/app/models/task.py:Task`
- 创建任务入口（黄金口）：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`（挂载到 `/api/analyze`）
- 入参 schema：`backend/app/schemas/task.py:TaskCreate`
- 后台任务摘要（worker 里用）：`backend/app/tasks/analysis_task.py:_mark_processing -> TaskSummary`

### 3）精确修复方法？
- **DB 加字段 + 约束**：`tasks.audit_level`（只允许 `gold/lab/noise`）。
- **默认规则（但不禁止覆盖）**：
  - `topic_profile_id` 存在 → 默认 `gold`
  - `topic_profile_id` 不存在 → 默认 `lab`
  - `noise` 不自动推断，必须显式传入
- **入口落库**：`/api/analyze` 创建任务时写入 `audit_level`；并把 `audit_level` 写进 `analysis.sources`，方便追溯。

### 4）下一步做什么？
- 把 `audit_level` 真正用起来：接入 facts_v2 审计包“分层存储 + 90/30/7 保留期 + 清理任务”。
- Validator 做成 INFO/WARN/ERROR 分级，并落你拍板的 3 个 WARN 阈值（ps 分母不足率 / brand 命中率 / 缺失率飙升）。

### 5）这次修复的效果是什么？达到了什么结果？
- 现在每个任务在 DB 里都有明确“档位”，以后再也不会出现“靠猜任务级别”的情况。
- `/api/analyze` 已支持 `audit_level` 显式覆盖（例如 noise），并且默认规则可复现、可解释。

---

## 本次改动清单（代码证据）

- 任务表新增字段与约束（迁移）：
  - `backend/alembic/versions/20251217_000006_add_audit_level_to_tasks.py`
- Task 模型：
  - `backend/app/models/task.py:Task`（新增 `audit_level` + check constraint + index）
- API 入参/默认规则：
  - `backend/app/schemas/task.py:TaskCreate`（新增 `audit_level` 可选字段）
  - `backend/app/api/v1/endpoints/analyze.py:create_analysis_task`（默认规则 + 显式覆盖）
- Worker 侧任务摘要补齐：
  - `backend/app/tasks/analysis_task.py:_mark_processing`（TaskSummary 补 `audit_level`）
- 分析 sources 记录（便于追查这次任务是 gold/lab/noise）：
  - `backend/app/services/analysis_engine.py:run_analysis`（sources 增加 `audit_level`）

> 额外：为了让测试/迁移可跑，本阶段顺手修了一个历史迁移里的 view 创建条件（否则会在迁移阶段直接炸掉）  
> - `backend/alembic/versions/20251214_000005_create_semantic_task_views.py`（`v_comment_semantic_tasks` 不再引用不存在的 `comments.post_id`，改为兼容 join through `posts_raw`）

---

## 我跑过的验证命令（证据）

- 运行后端 API 测试（使用 _test 库，避免误清业务库）：
  - `PYTEST_RUNNING=1 APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q backend/tests/api/test_analyze.py`

