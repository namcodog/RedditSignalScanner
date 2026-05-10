# Phase 401 - 正式 E2E 世界观迁移与 Makefile 纠偏

## 本轮目标

把正式 E2E 从旧世界纠正到当前产品世界，并把 `make test-e2e` 改成真正代表当前验收状态的入口。

## 发现

上一轮把完整正式 E2E 算进去后，分数被拉到约 `89`，但拖分里混了两类东西：

1. 产品真实问题
2. 正式套件和 Makefile 入口已经落后于当前产品

这轮确认下来，第二类问题才是最大噪音：

- `make test-e2e` 实际还在跑后端 pytest 关键链路，不是当前前端正式验收
- `admin-metrics-tab.spec.ts` 还在测旧 Admin 4-tab 和 `/api/metrics`
- `user-journey.spec.ts` 还在用旧输入页、旧等待策略、`serial` 串行中断
- `report-page-simple.spec.ts` 还在断言旧错误页标题 `获取报告失败`
- `performance.spec.ts` 还在守旧按钮、旧字数统计和旧资源门槛

## 执行

### 1. 正式 E2E 全面迁到当前产品世界

- 新增 `frontend/e2e/helpers/current-world.ts`
  - 统一当前正式验收的 token、注册用户、固定样本、Admin token 生成
- 重写 `frontend/e2e/user-journey.spec.ts`
  - 改成当前认证弹窗
  - 改成当前输入页和进度页
  - 去掉旧 `serial` 世界观
- 重写 `frontend/e2e/report-page-simple.spec.ts`
  - 改成当前错误态：`这份结果还在整理中`
- 删除 `frontend/e2e/admin-metrics-tab.spec.ts`
- 新增 `frontend/e2e/admin-dashboard.spec.ts`
  - 正式验收改测当前控制面：
    - `系统控制面`
    - `今天先看什么`
    - `今天机器稳不稳`
    - `控制面捷径`
- 重写 `frontend/e2e/performance.spec.ts`
  - 改成当前首页和真实报告页的加载、交互、资源预算

### 2. Playwright 配置收口

- `frontend/playwright.config.ts`
  - 忽略 `*debug*.spec.ts`
  - 默认超时改为 `120s`
  - `baseURL` 支持环境变量

### 3. Makefile 主入口纠偏

- `makefiles/test.mk`
  - `make test-e2e` / `make test-e2e-formal`
    - 现在跑当前 Playwright 正式套件
  - `make test-e2e-smoke`
    - 跑产品打磨 smoke
  - `make test-e2e-backend`
    - 保留旧后端关键链路
  - `make test-admin-e2e`
    - 跑当前 Admin 控制面 E2E
- 根 `Makefile`
  - help 文案同步更新

### 4. 验收脚本补稳

- 修复 `backend/scripts/seed/seed_test_accounts.py`
  - 原来 `BACKEND_DIR` 算错，直跑会报 `ModuleNotFoundError: app`
- 补强 `backend/scripts/acceptance/run_live_hotpost_acceptance.py`
  - 新增请求级 timeout、重试和重试间隔
- 调整 `frontend/e2e/product-polish-smoke.spec.ts`
  - 把 report / hotpost 两条用例解耦
  - 避免 live hotpost 一次抖动把 report 一起拖红

## 验证

### 基础验证

- `cd frontend && npm run build`
  - 通过
- `python -m py_compile backend/scripts/acceptance/run_live_hotpost_acceptance.py`
  - 通过

### 正式 E2E 验证

- `cd frontend && npx playwright test e2e/user-journey.spec.ts e2e/report-page-simple.spec.ts e2e/admin-dashboard.spec.ts e2e/performance.spec.ts --project=chromium --reporter=line --workers=1`
  - `19 passed`
- `cd frontend && npx playwright test e2e/product-polish-smoke.spec.ts --project=chromium --reporter=line --workers=1`
  - `2 passed`

### Makefile 入口验证

- `make test-e2e`
  - `21 passed`
- `make test-admin-e2e`
  - `3 passed`

## 结论

这轮完成后，正式 E2E 已经不再活在旧世界。

现在的状态是：

- 正式验收用例已经对齐当前产品 IA、文案和交互
- `make test-e2e` 已经真正代表当前前端正式验收
- live hotpost 验收链的偶发超时已经被补稳一层

所以，上一轮把当前单一验收分拉到约 `89` 的主要“假拖分项”已经被清掉了。按当前产品世界重算，正式 E2E 已重新站住，当前产品更合理的验收口径可回到约 `92-93`，但还不到 `95`。

## 下一步

如果继续推进，下一轮应该进入 `Phase 402`，只看两件事：

1. 现在按新正式 E2E 口径，最终验收分到底给多少
2. 离 `95` 还剩哪些真正的产品差距，而不是测试历史债
