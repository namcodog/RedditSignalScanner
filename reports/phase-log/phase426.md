# Phase 426 - 正式 E2E 登录竞态修复

## 背景

- 在上一轮收尾回归中，`make test-e2e` 出现 `1/21` 失败。
- 失败集中在 `frontend/e2e/user-journey.spec.ts` 的登录场景。

## 根因

- 用例在登录提交后，直接用 `page.evaluate(() => localStorage.getItem('auth_token'))` 做轮询。
- 页面发生跳转时，浏览器会销毁当前执行上下文，导致偶发报错：
  - `Execution context was destroyed, most likely because of a navigation`

这属于测试层等待策略竞态，不是产品功能回退。

## 修复

- 文件：`frontend/e2e/user-journey.spec.ts`
- 新增 `readAuthTokenSafely(page)`：
  - 对导航期间的 `evaluate` 异常做容错，返回 `null` 并继续轮询。
- 更新两处断言：
  - `waitForAuthToken` 改为安全轮询（15s）
  - 错误密码场景“应无 token”也改为安全轮询（15s）

## 验证

- 定向稳定性回归：
  - `cd frontend && npx playwright test e2e/user-journey.spec.ts --project=chromium --workers=1 --reporter=line --repeat-each=3`
  - 结果：`21 passed`
- 正式全量回归：
  - `make test-e2e`
  - 结果：`21 passed`

## 结论

- 正式 E2E 已恢复全绿。
- 当前阶段的主要阻塞已清除，后续可以继续推进 95+ 的最后一层体验精修。
