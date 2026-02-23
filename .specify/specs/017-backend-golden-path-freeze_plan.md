# Implementation Plan: 冻结后端黄金路径（/api）& legacy 观察期

**Date**: 2025-12-16  
**Scope**: 仅后端 + 数据库（不含前端 UI）  
**Goal**: 把“主干路”钉死为 `/api`，并用运行时指标证明 legacy 调用为 0（或能解释清楚），为后续清理铺路。  

## Summary（只以代码为准）

当前 FastAPI 实际挂载为：

- 主入口路由前缀：`/api`（`backend/app/main.py:create_application` → `include_router(..., prefix="/api")`）
- v1 目录仅是代码组织，不等于 `/v1` 门牌（`backend/app/api/v1/api.py:api_router = APIRouter()`）
- legacy 路由同样挂在 `/api` 下（`backend/app/main.py:create_application` → `legacy_router = APIRouter(prefix="/api")`）

因此我们先冻结黄金路径为 `/api`（改动最小、最快跑稳），稳定后再考虑新增 `/api/v1` 作为“新门牌”（先不进入 E2E 主线）。

## Contract（门牌契约）

### 1) 黄金路径（Golden Path）

**定义**：端到端（E2E）测试与生产主线只走这条路，并稳定通过。

约束：
- 所有对外“主线接口”必须在 `/api` 下可用
- 任何“deprecated/use xxx” 提示不得指向不存在的路径
- 任何变更必须先更新契约测试，再改实现

### 2) 旧路（Legacy）

**定义**：仍挂载，但不得被主线调用；需可观测并满足观察期后清理。

约束：
- 运行时指标能区分 legacy vs golden 的调用量
- 观察期内 legacy 调用为 0（或每个非 0 都能定位到调用方并给迁移计划）

## Deliverables（可交付物）

- `backend/tests/api/test_golden_path_contract.py`：黄金门牌契约测试（先写测试再实现）
- `backend/app/middleware/route_metrics.py`（或同等位置）：按路由组统计调用量（golden vs legacy），写入 Redis（可关）
- `backend/app/tasks/monitoring_task.py`：读取上述指标并上报 dashboard（用于观察期验收）
- `reports/phase-log/phase18.md`：本阶段记录（以代码证据为准，写清冻结的门牌契约与观察期标准）

## Constraints & Guardrails

- 不做“大改路由重构”，只做“钉门牌 + 统计 + 验收”
- 不改业务算法；涉及 DB 仅做“可追溯字段/记录”必要补强（优先轻量写不读）
- 所有变更必须可回滚（开关/旁路）

