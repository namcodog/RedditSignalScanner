# Phase 28 - Facts v2 “审计包”从脚本捡回：接入 /api 主线并落库可追溯

日期：2025-12-17  
范围：仅后端 + 数据库；不改业务口径，不改前端，不引入新门牌（仍冻结 `/api`）。

## 一句话结论

以前 facts_v2 的“审计包”主要活在脚本里（落文件、插一张 audit 表），API 主线跑完只剩报告，**回头很难问清：这份报告到底基于哪些事实、门禁当时怎么判的**。  
本阶段把这块“黑匣子”补上：**分析跑完会把 facts_v2 审计包落库（facts_snapshots），并提供 admin 接口一键拉出来看。**

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- facts_v2 的“完整审计包”在 `backend/scripts/generate_t1_market_report.py` 里很完整，但 **API 主线**（`backend/app/services/analysis_engine.py:run_analysis`）只做了一个“门禁用最小包”，算完就丢了。
- 结果就是：报告是有了，但你要追查“当时样本够不够、哪块缺口导致降级/拦截”，缺少一个稳定落库的证据源。

### 2）是否已精确定位？
- API 主线门禁包构造点：`backend/app/services/analysis_engine.py:run_analysis`（局部变量 `facts_v2_package`）
- 分析落库总入口：`backend/app/tasks/analysis_task.py:_store_analysis_results`
- 新增落库载体：`backend/app/models/facts_snapshot.py:FactsSnapshot` + `backend/alembic/versions/20251217_000004_add_facts_snapshots.py`

### 3）精确修复方法？
- **加一张专用表**：`facts_snapshots` 存每次分析的 facts_v2 审计包（JSONB）+ 闸门结论（tier/passed/quality）。
- **接入主线**：
  - `run_analysis` 把 `facts_v2_package` 挂到 `sources`（用于传递）
  - `_store_analysis_results` 把 `facts_v2_package` 从 `sources` 里 `pop` 出来，落到 `facts_snapshots`，并把 `facts_snapshot_id` 写回 `sources`（方便反查）
- **补一个 admin 拉取口**：能按 task_id 直接拿最新快照，排查不用翻库。

### 4）下一步做什么？
- 把 API 主线的 `facts_v2_package` 从“门禁最小包”升级到 SOP 那套更完整的结构（至少补齐：time_window、diagnostics、evidence quotes、data_lineage 指纹、validator 结果）。
- 再评估：是否要对所有任务都落快照，还是只对“黄金模式/带 topic_profile 的任务”落快照；以及保留周期（7/30/90 天）。

### 5）这次修复的效果是什么？达到了什么结果？
- 现在你拿任意一个 `task_id`，能直接查到：这次分析的 facts_v2 审计包 + 门禁结果（A/B/C/X），不再“只有报告没有证据”。
- 这套改动是**增量增强**：不改变现有报告生成逻辑，只增加“可追溯黑匣子”。

---

## 本次改动清单（代码证据）

- 新增模型与迁移：
  - `backend/app/models/facts_snapshot.py`
  - `backend/alembic/versions/20251217_000004_add_facts_snapshots.py`
  - `backend/app/models/task.py`（挂上 `facts_snapshots` 关系）
- 接入分析主线落库：
  - `backend/app/services/analysis_engine.py:run_analysis`（把 `facts_v2_package` 放进 `sources`）
  - `backend/app/tasks/analysis_task.py:_store_analysis_results`（落 `facts_snapshots` + 写回 `facts_snapshot_id`）
- Admin 查询口：
  - `backend/app/api/admin/facts.py`
  - `backend/app/api/routes/__init__.py`
  - `backend/app/main.py`（include router）

---

## 我跑过的验证命令（证据）

- `cd backend && DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test alembic upgrade heads`
- `cd backend && PYTEST_RUNNING=1 SKIP_DB_RESET=1 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q tests/tasks/test_facts_snapshots.py`
- `cd backend && PYTEST_RUNNING=1 SKIP_DB_RESET=1 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q tests/api/test_admin_facts_snapshots.py`

