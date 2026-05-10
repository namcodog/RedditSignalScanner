# Phase 423 - Phase 28 精品化第一刀（Input/Progress）

## 目标

继续冲 95+ 的体验精品化，不改能力层，只收交互手感和文字密度。

## 本轮改动

- 文件：`frontend/src/pages/ProgressPage.tsx`
  - 运行中描述从「数据收集与处理」改为更直观的「系统正在抓取并分析真实讨论」。
  - 页面主容器加入轻量入场过渡（fade + slide），减少切页突兀感。
  - 运行提示继续减字：
    - 「只要进度和阶段还在变化」->「阶段在变」
    - 「中途返回不会丢掉你刚才的产品描述」->「中途返回不丢描述」
  - warmup 保留两条主动作（看当前结果 / 回输入页重跑），移除第三个低价值动作按钮，减少决策负担。
  - 取消确认文案和按钮收口：
    - `回到首页` -> `回输入页`
    - 描述改为更明确的“回输入页继续改后重跑”。

- 文件：`frontend/src/pages/InputPage.tsx`
  - 带回提示和首屏说明继续压缩，减少“说明味”。
  - 主内容容器加入轻量入场过渡，和 Progress 保持一致节奏。
  - 示例说明进一步收短，保留“只起草，不生成示例报告”的核心信任语义。

- 测试同步
  - `frontend/src/pages/__tests__/ProgressPage.test.tsx` 同步新文案和按钮名称断言。

## 验证

- 定向测试：
  - `cd frontend && npm run test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ProgressPage.test.tsx`
  - 结果：`13/13 passed`
- 前端构建：
  - `cd frontend && npm run build` 通过
- 完整正式 E2E：
  - `make test-e2e` 结果：`21/21 passed`

## 结果

- Input/Progress 的阅读阻力继续下降，动作决策更干净。
- 在不牺牲稳定性的前提下，交互手感更接近成品。
