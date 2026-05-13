# Phase 289 - API / 前端展示模块第一轮整治（用户侧输出面）

## 1. 发现了什么？

- 后端 `ReportPayload` 已经开始把真实 `sources` 带出来，但前端报告类型和 schema 还停在旧口径。
- 结果就是：
  - 后端已经说真话
  - 前端合同却把这些字段截断
  - 页面、测试、AI 都看不到真实的 `report_tier / structured_llm_status / communities_detail`

## 2. 是否需要修复？

- 需要。
- 这轮没有改数据库表结构，没有新 migration。
- 改的是用户侧报告接口合同、前端类型、schema 和对应测试。

## 3. 精确修复方法？

- 补齐前端报告合同：
  - `frontend/src/types/analysis.types.ts`
  - `frontend/src/types/report/response.ts`
  - `frontend/src/types/report/schema.ts`
  - `frontend/src/types/index.ts`
- 让用户侧报告正式接住后端新增的 `sources` 字段：
  - `communities_detail`
  - `report_tier`
  - `structured_llm_status`
  - `structured_llm_reason`
  - 以及其他当前真实来源字段
- 对齐用户侧页面和契约测试：
  - `frontend/src/tests/contract/report-schema.contract.test.ts`
  - `frontend/src/tests/contract/report-api.contract.test.ts`
  - `frontend/src/services/__tests__/analyze.api.test.ts`
  - `frontend/src/pages/__tests__/ReportPage.test.tsx`
  - `frontend/src/pages/__tests__/ReportFlow.integration.test.tsx`
  - `frontend/src/utils/__tests__/report-types.test.ts`

## 4. 下一步系统性的计划是什么？

- 用户侧输出面这一刀完成后，继续整治同一模块里的 admin 控制面。
- 原则不变：
  - 文档口径统一
  - 代码接口统一
  - 测试门禁锁住

## 5. 这次执行的价值是什么？达到了什么目的？

- 这轮把“后端已经说真话，但前端合同没接住”这个断点补上了。
- 现在用户侧报告接口不再静默丢掉后端真实状态。

## 验证

- `cd frontend && npm run test -- src/tests/contract/report-schema.contract.test.ts src/tests/contract/report-api.contract.test.ts src/services/__tests__/analyze.api.test.ts src/pages/__tests__/ReportFlow.integration.test.tsx src/pages/__tests__/ReportPage.test.tsx src/utils/__tests__/report-types.test.ts`
  - `10 passed`
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
