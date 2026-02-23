# Phase 18 - 冻结后端黄金路径（/api）第一步：门牌契约测试 + 文案对齐

日期：2025-12-16  
代码基线：`main@fbc5a89`（工作区 dirty；本阶段以当前代码实况为准）

## 一句话结论

把“黄金路径=/api”这件事先变成**可验证的契约测试**：修正了 `/api/healthz` 的误导性提示、修正根路径 `/` 的端点清单，并补上了黄金门牌契约测试；同时修复了一个会导致后端无法 import 的语法错误（IndentationError），避免系统“直接起不来”。

---

## 我查到的证据（以代码为准）

- 黄金路径真实挂载点：`backend/app/main.py:create_application`（`include_router(..., prefix="/api")`）
- v1 目录只是代码组织，不等于 `/v1` 门牌：`backend/app/api/v1/api.py:api_router = APIRouter()`
- 新增黄金门牌契约测试：`backend/tests/api/test_golden_path_contract.py`
- 修复 healthz 文案 + 根路径端点清单：`backend/app/main.py`
- 修复语法错误（阻断 import）：`backend/app/services/semantic/smart_tagger.py`

---

## 端到端链路（本期涉及段）

（门牌/契约层）调用方 → `/api/*` 路由表 → handler →（本期不触达）DB/Celery/分析 → 返回

本期主要在“门牌/对外说法”这一层加安检门（契约测试），不改业务算法。

---

## 统一反馈五问（结果可复现）

### 1）发现了什么问题/根因？
- `/api/healthz` 返回的 `deprecated` 文案指向不存在的路径：`use /api/v1/healthz`（门牌没冻结导致“说法和现实不一致”）。
- 根路径 `/` 返回的 `endpoints` 清单包含不存在的路径（`/api/stream/{task_id}`、`/api/tasks/{task_id}`、`/api/reports/{task_id}`）。
- 后端存在一个会导致 import 失败的语法错误：`backend/app/services/semantic/smart_tagger.py` 出现重复粘贴块，触发 `IndentationError`，导致测试/服务启动直接崩。

### 2）是否已精确定位？
是。
- 证据：`backend/tests/api/test_golden_path_contract.py` 在修复前可稳定复现失败点：
  - `Healthz deprecated points to missing route: use /api/v1/healthz`
  - `Root endpoints list contains nonexistent routes: ...`
- 语法错误定位到：`backend/app/services/semantic/smart_tagger.py`（重复的 `NOISE_KEYWORDS` 片段）。

### 3）精确修复方法？
- `backend/app/main.py`：
  - `/api/healthz` 去掉误导性 `deprecated` 文案（不再指向不存在路径）。
  - 根路径 `/` 的 `endpoints` 清单改为与实际存在路由一致（`/api/analyze/stream/{task_id}`、`/api/report/{task_id}`、`/api/export/csv` 等）。
- `backend/app/services/semantic/smart_tagger.py`：
  - 删除重复粘贴导致的多余块，消除 `IndentationError`。

### 4）下一步做什么？
按 `.specify/specs/017-backend-golden-path-freeze_tasks.md` 继续往下做：
1) legacy vs golden 调用计数（中间件 + 观察期指标）  
2) 最小血缘写入 `Analysis.sources`（先写不读，保证可追溯/可复现）

### 5）这次修复的效果是什么？
- 黄金门牌契约测试已落地并通过：`SKIP_DB_RESET=1 pytest -q backend/tests/api/test_golden_path_contract.py`（本地验证通过）。
- 后端模块可正常 import（`IndentationError` 消失），避免“服务/测试直接起不来”的硬故障。

---

## 本次变更清单（文件级）

- ✅ 新增：`backend/tests/api/test_golden_path_contract.py`
- ✅ 修改：`backend/app/main.py`
- ✅ 修改（修复语法错误）：`backend/app/services/semantic/smart_tagger.py`
- ✅ 新增（任务落地用）：`.specify/specs/017-backend-golden-path-freeze_plan.md`
- ✅ 新增（任务落地用）：`.specify/specs/017-backend-golden-path-freeze_tasks.md`

