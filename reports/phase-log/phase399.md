# Phase 399 - 清理旧 warning，确认 95 分前最后差距

## 本轮目标

把 `Phase 398` 留下的两条旧 warning 清掉，再确认这次清理是不是只是“安静了”，还是确实把产品验收的完成感和稳定性再往前推了一格：

- 清理 `React.jsx type is invalid`
- 清理 `baseline-browser-mapping` 过期提示
- 回归主链路测试、构建和 smoke E2E
- 判断当前是否真的更接近 `95`

## 完成情况

### 1. `React.jsx type is invalid` 已确认根因并修掉

这条 warning 不是组件没导出，而是一个典型的循环依赖：

- `ReportPage -> import { ROUTES } from '@/router'`
- `router/index.tsx -> import ReportPage`

在测试环境里，这会让 router 在构造 `<ReportPage />` 时撞上未稳定的模块绑定，于是 React 报 `type is invalid`。

这次的修法不是打补丁，而是把路由常量正式拆出去：

- 新增 `frontend/src/router/routes.ts`
- 页面统一从 `@/router/routes` 取 `ROUTES`
- `router/index.tsx` 只负责路由定义，并保留对 `ROUTES` 的 re-export

修完后，`ReportPage` 定向测试启动时，这条 warning 已经不再出现。

### 2. `baseline-browser-mapping` 过期提示已清掉

本轮把前端依赖里的 `baseline-browser-mapping` 升到了：

- `2.10.8`

对应文件：

- `frontend/package.json`
- `frontend/package-lock.json`

升级后，vitest 启动时那条“数据已过期”的提示已经消失。

### 3. 回归验证已经补齐

已通过：

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx \
  src/pages/__tests__/InputPage.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx
```

结果：

- `4 files passed / 18 tests passed`

已通过：

```bash
cd frontend && npm run build
```

已通过：

```bash
cd frontend && npx playwright test e2e/product-polish-smoke.spec.ts --project=chromium --reporter=line
```

结果：

- 二次重跑：`2 passed`

已通过：

```bash
cd frontend && npx playwright test e2e/product-polish-smoke.spec.ts --project=chromium --reporter=line --repeat-each=2
```

结果：

- `4 passed`

## 本轮额外发现

### 1. smoke E2E 存在一次环境级瞬时波动

第一次重跑 smoke E2E 时，不是页面挂了，而是：

- `backend/scripts/acceptance/run_live_hotpost_acceptance.py`

在发起 live hotpost 查询时打后端超时。

随后我做了两步确认：

1. 单独执行脚本，成功返回新的 `query_id`
2. 立即重跑 E2E，`2 passed`
3. 再做 `repeat-each=2`，`4 passed`

所以这次更像验收环境瞬时波动，而不是本轮 warning 清理造成的回归。

### 2. 当前“开发中味道”确实又淡了一层

这轮不改用户主界面，但值钱的地方在：

- 启动测试时不再冒出那两条老 warning
- 路由模块关系更干净
- smoke E2E 复验更稳

这会直接抬高“这套产品是不是已经收住”的感觉。

## 关键改动文件

- `frontend/src/router/routes.ts`
- `frontend/src/router/index.tsx`
- `frontend/src/pages/InputPage.tsx`
- `frontend/src/pages/ProgressPage.tsx`
- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/InsightsPage.tsx`
- `frontend/src/pages/DecisionUnitsPage.tsx`
- `frontend/package.json`
- `frontend/package-lock.json`

## 当前产品分数

按产品标准，我会把当前判断从 `Phase 398` 的约 `92`，轻微上调到：

- `93`

我会这样拆：

1. 价值硬度：`90`
2. 体验顺滑度：`92`
3. 真实交付可信度：`95`
4. 产品完成感：`93`

这次加分不靠新功能，而是靠：

- 旧 warning 被清掉
- 真链路回归更稳
- 验收时的“开发中气味”继续下降

## 为什么还不是 95

还差的已经非常收敛：

### 1. 视觉密度和过渡手感还没做最后一刀

现在已经成熟，但还没到“每一屏都特别利落”的精品状态。

### 2. 验收环境还没完全去波动

虽然重跑和复验都通过了，但 live hotpost 入口仍然偶发超时，这说明：

- 产品主链没问题
- 验收链还值得再补一层重试和容错

### 3. 还剩几条非主目标 warning

现在还会看到一些非阻塞提示：

- React Router future flag warning（测试环境）
- 个别 error-case 测试里的预期 `console.error`
- Playwright 的 `NO_COLOR/FORCE_COLOR` 环境 warning
- acceptance token 里的 JWT key length warning
- build 的 chunk size warning

这些不属于本轮那两条旧 warning，但如果真要冲 `95`，就该挑最值钱的再清一轮。

## 下一步

如果继续冲，我建议进入一个很短的 `Phase 400`：

1. 收最后一层视觉密度和过渡手感
2. 给 live hotpost 验收脚本补超时重试
3. 再做一次浏览器截图级精品验收
4. 最后再决定能不能给 `95`

如果不继续冲：

- 我认为当前可以按约 `93` 分阶段验收
