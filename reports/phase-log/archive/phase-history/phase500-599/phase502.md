# Phase 502 - 无 Playwright 稳定验收入口固化

## 时间
- 2026-03-27

## 目标
- 回应“Playwright 不稳定时如何验收”的问题。
- 在项目内固化一条不依赖浏览器 E2E 的稳定验收命令。

## 变更
- 文件：`makefiles/test.mk`
- 新增：
  - 变量：`FRONTEND_STABLE_CONTRACT_SPECS`
  - 目标：`acceptance-stable-no-playwright`
- 执行顺序（单命令串联）：
  1. `acceptance-offline-gate`
  2. 前端契约/集成测试（Vitest）
  3. `acceptance-live-smoke`
  4. `acceptance-live-final`

## 验证
- 前端契约+集成：
  - `npm test -- --run src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportFlow.integration.test.tsx`
  - 结果：`6 passed`
- 后端离线门禁：
  - `make acceptance-offline-gate`
  - 结果：`65 passed`
- 说明：
  - `make -n acceptance-stable-no-playwright` 在当前环境触发了递归 make 子目标执行（并非纯打印），后续使用时建议直接跑真命令，不以该命令做 dry-run 判定。

## 四问回顾
1. 发现了什么？
- Playwright 在当前链路中不是稳定依赖，必须有无浏览器验收主链。

2. 是否需要修复？
- 需要，已修复为统一入口命令。

3. 精确修复方法？
- 在 Makefile 增加 `acceptance-stable-no-playwright`，把后端门禁、前端契约、live smoke、live final 串起来。

4. 下一步系统性计划是什么？
- 继续收尾第 2 环：用 final task 做一次人工前端可视验收。
- 收尾第 3 环：把该命令写入 README/运维文档“标准验收入口”。

5. 这次执行的价值是什么？
- 验收链从“依赖 Playwright”升级为“Playwright 可选”，系统稳定性更可控。
