# Reddit Signal Scanner — Architecture Overview (2025-09-27)

## 1. Purpose
本文件用于快速理解仓库结构、关键模块的职责与调用关系，同时作为“零冗余”治理的结构基线。所有新增代码需遵循本文描述的边界与命名规范，任何弃用资产必须在提交前清理。

## 2. Repository Map
```
.
├── backend/                 # FastAPI + Celery 服务端
│   ├── app/                 # 生产代码（分层：api/core/services/tasks/models/schemas）
│   ├── config/              # YAML/ENV 配置模板
│   ├── alembic/             # 数据库迁移脚本
│   ├── scripts/             # 运维/巡检脚本
│   ├── tests/               # 后端测试
│   └── data/                # 结构化基准数据
├── frontend/                # Vite + React 前端
│   ├── src/
│   │   ├── api/             # API/SSE 客户端
│   │   ├── components/      # UI 组件（含 ui/）
│   │   ├── pages/           # 页面与 Admin 页面
│   │   ├── services/        # 业务服务封装
│   │   ├── hooks/           # 状态管理、上下文
│   │   ├── router/          # 客户端路由与守卫
│   │   ├── types/ & utils/  # 公共类型与工具
│   │   └── __tests__/       # Vitest 用例
│   ├── tests/               # 独立测试资产
│   └── e2e/                 # Playwright 场景
├── tests/                   # 全局测试框架（smoke / integration / perf / chaos）
├── infrastructure/          # 预留目录（当前未落地）
├── scripts/                 # 对外/一次性脚本（需持续审计）
├── makefiles/               # Makefile 拆分模块
├── docs/                    # 产品/运维/架构文档
├── reports/                 # 阶段验收与执行记录
├── .specify/                # 规格与计划基线
└── data/                    # 数据资产与临时导出
```

## 3. Module Boundaries & Allowed Dependencies
- `backend/app/api` 只能依赖 `core`, `services`, `schemas`, `models`；禁止直接读取 `database` 或脚本目录。
- `backend/app/services` 可依赖 `core`, `models`, `schemas`, `algorithms`, `utils`，但不得反向被 `core` 依赖。
- `backend/app/tasks` 调用 `services` 完成业务逻辑，不得直接访问 `api`。
- `frontend/src/pages` 只通过 `services`/`hooks` 访问 API，不直接耦合底层 HTTP 客户端。
- 顶层 `tests/` 应通过公共夹具调用服务/前端构建，禁止把生产代码复制到测试目录。

以上边界当前通过代码审查与目录治理流程保证，结构校验脚本尚未落地。

## 4. High-Level Data Flow
1. **任务创建**：`frontend` → `POST /api/analyze` (FastAPI) → `tasks` 表
2. **异步处理**：Celery Worker (`app/tasks/analysis_task.py`) → 数据采集 + 分析引擎 (`app/services/analysis_engine.py`)
3. **状态推送**：`GET /api/analyze/stream/{task_id}` (SSE) → EventSource
4. **结果呈现**：`GET /api/report/{task_id}` 返回结构化报告
5. **质量账本**：`GET /api/tasks/{task_id}/sources` 解释 tier/降级原因
6. **决策单元**：`/api/decision-units` 提供平台级可复用决策与反馈
7. **管理面**：`/api/admin/*` 提供任务监控、审计与社区池管理（已同步）

## 5. Build & Quality Pipeline
- **本地启动**：严格按照 `make backend-hard-restart → make dev-up → curl 健康检查 → make sse-test → make quick-gate-local → make openapi-check-stream` 顺序执行。
- **类型门控**：`make type-check`（后端 MyPy + 前端 TS 检查）即将升级为阻塞项，核心与测试均需 0 报错。
- **测试分类**：`tests/` 目录承担全局冒烟/集成/性能；`backend/tests/` 与 `frontend/src/__tests__` 则是局部单元测试。清理完成后，将统一调度入口。
- **结构巡检**：当前无自动脚本，依赖手工审查与目录规范保障无冗余。

## 6. Naming & Location Conventions
- 新增后端模块优先落在 `backend/app/services|core|api` 对应层级；禁止在根目录放置临时 `.py`。
- 所有脚本必须位于 `scripts/` 或 `backend/scripts/`，历史脚本进入归档目录。
- 测试文件遵循 `tests/<domain>/test_*.py`，夹具统一放在 `tests/fixtures/` 或 `backend/tests/fixtures/`。
- 前端组件使用 PascalCase 命名，Hooks 使用 `useXxx`，服务层使用 `something.service.ts`。

## 7. Governance Checklist (for Zero-Redundancy Initiative)
1. 任何 PR 必须：
   - 提供对应目录的更新说明
   - 确认未新增“孤儿”文件或脚本
   - 运行 `make quick-gate-local` 并附结果
2. 每周巡检：
   - 运行结构校验脚本，确保目录与本文一致
   - 核对 `docs/`、`reports/` 内容与仓库状态同步
   - 清理 `tmp/`、`mock_data/` 中的临时资产
3. 弃用流程：
   - 标记文件 → 开 PR 删除 → 更新文档 → 在下一次巡检确认无引用

---
本文档会随着代码结构调整定期更新，任何结构性改动必须同步修订本文件及 `Reddit信号扫描器-全仓库深度分析报告` 对应章节。
