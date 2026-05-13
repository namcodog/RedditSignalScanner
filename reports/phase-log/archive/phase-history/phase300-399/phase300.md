# Phase 300 - API/前端展示模块第二轮第一刀：admin API 控制面拆域

## 背景

第二轮结构性收口推进到 API / 前端展示模块。
这轮聚焦 admin 控制面前端 API 层，目标不是改页面行为，而是把前端控制面从单个 God file 收成清晰的分域接口层，同时保留一个稳定出口，降低后续页面、测试和 AI 理解的耦合成本。

## 发现

- `frontend/src/api/admin.api.ts` 同时承载 dashboard、communities、imports、governance、tasks/diagnostics 等多类控制面接口，已经演变成单文件真相源过重的问题。
- 页面和兼容层都依赖 `@/api/admin.api`，如果直接改页面导入，波及面太大，不符合第二轮“稳稳推进”的节奏。
- 最合适的结构性收口方式是：
  - 内部按域拆分实现
  - 外部继续保留单一公开入口
  - 让页面和兼容层不感知本轮内部重组

## 修复

### 1. admin API 按域拆分

新增分域 API 文件：

- `frontend/src/api/admin/dashboard.api.ts`
- `frontend/src/api/admin/communities.api.ts`
- `frontend/src/api/admin/imports.api.ts`
- `frontend/src/api/admin/governance.api.ts`
- `frontend/src/api/admin/tasks.api.ts`

职责划分：

- `dashboard.api.ts`：仪表盘统计
- `communities.api.ts`：社区汇总、候选社区、社区池、调级建议、审计日志
- `imports.api.ts`：社区 Excel 导入、模板下载、导入历史
- `governance.api.ts`：治理快照、有效社区、cleanup-dev
- `tasks.api.ts`：活跃用户、任务队列、质量指标、诊断、任务账本

### 2. 保留单一公开出口

`frontend/src/api/admin.api.ts` 改成薄 barrel：

- 只做显式 re-export
- 不再承载具体请求实现
- 继续作为页面和 `admin.service.ts` 的唯一公开前端 API 入口

这轮没有改页面调用方式，页面仍然统一从 `@/api/admin.api` 导入。

### 3. 控制面接口结构性收益

- `admin.api.ts` 行数从 `499` 降到 `77`
- admin 控制面前端 API 从“一个超大文件”收成“多域实现 + 单一出口”
- 页面、兼容层、测试不需要重新学习第二套入口

## 验证

### 前端定向测试

```bash
cd frontend && npm run test -- \
  src/services/__tests__/admin.service.test.ts \
  src/pages/__tests__/AdminDashboardPage.test.tsx \
  src/pages/__tests__/TaskLedgerPage.test.tsx
```

结果：

- `11 passed`

### 前端构建

```bash
cd frontend && npm run build
```

结果：

- build 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 价值

这轮不是功能扩展，而是把 admin 控制面的前端 API 边界真正拆清：

- 页面继续只认一个出口
- 内部实现不再绑死在单文件 God API 上
- 后续 admin 页面继续整治时，可以按域推进，而不是继续在一个大文件上互相牵连

这更符合第二轮的目标：

- 职责更单一
- 接口更稳定
- 耦合更低
- 控制面更像一套真正可维护的系统齿轮
