# Phase 290 - API / 前端展示模块第二轮整治（Admin 控制面）

## 1. 发现了什么？

- Admin 控制面前端长期存在两套访问层：
  - `frontend/src/api/admin.api.ts`
  - `frontend/src/services/admin.service.ts`
- 页面大多已经直连 `admin.api.ts`，但旧测试和兼容层还在手搓另一套请求。
- 这会导致：
  - 前后端契约漂移
  - 页面、测试、旧壳各说各话
  - Admin 控制面不再有一个真正的前端真相源

## 2. 是否需要修复？

- 需要。
- 这轮没有改数据库表结构，没有新 migration。
- 改的是 admin 控制面前端访问层、兼容壳和测试合同。

## 3. 精确修复方法？

- 把 `frontend/src/api/admin.api.ts` 补成 admin 控制面的唯一前端 API 真相源：
  - 补齐社区汇总、导入、诊断、治理快照等类型和请求函数
  - `approve/reject` 改成真实返回值，不再假装 `void`
  - `importCommunities` 支持 `dryRun + onUploadProgress`
  - 新增治理接口：
    - `getCommunityGovernanceSummary`
    - `getEffectiveCommunities`
    - `cleanupCommunityGovernanceDev`
- 把 `frontend/src/services/admin.service.ts` 收成薄兼容层：
  - 不再自己手搓请求
  - 统一委托给 `admin.api.ts`
  - 仅保留旧参数到新接口的轻量兼容转换
- 对齐页面和测试到当前真实依赖：
  - `frontend/src/services/__tests__/admin.service.test.ts`
  - `frontend/src/pages/__tests__/AdminDashboardPage.test.tsx`
  - `frontend/src/pages/__tests__/TaskLedgerPage.test.tsx`

## 4. 下一步系统性的计划是什么？

- API / 前端展示模块第一轮整治到这里算完整了：
  - 用户侧输出面
  - Admin 控制面
- 下一步可以回到总整治节奏，做第一轮总复盘，再决定是否进入第二轮结构降耦合。

## 5. 这次执行的价值是什么？达到了什么目的？

- 这轮把 admin 控制面从“前端两套访问层并存”，收成了“一个真相源 + 一个薄兼容壳”。
- 这样以后页面、测试、AI 都不需要再猜到底该信哪一层。

## 验证

- `cd frontend && npm run test -- src/services/__tests__/admin.service.test.ts src/pages/__tests__/AdminDashboardPage.test.tsx src/pages/__tests__/TaskLedgerPage.test.tsx`
  - `11 passed`
- `cd frontend && npm run build`
  - 通过
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 残留噪音

- 前端仍有已有 warning：
  - `baseline-browser-mapping` 过期提示
  - React Router v7 future flag 提示
  - Vite chunk size 提示
- 这些是噪音，不是本轮回归。
