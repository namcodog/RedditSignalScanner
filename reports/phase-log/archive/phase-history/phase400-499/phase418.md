# Phase 418 - 输入/等待页减负与真实链路信任强化

## 目标

把 `Input + Progress` 从“说明偏多”继续收成“第一眼能懂、马上能动”的节奏，同时降低示例态在报告首屏的视觉权重，强化真实链路感知。

## 本轮改动

### 1) Input 页文案减负（不改主链结构）

- 文件：`frontend/src/pages/InputPage.tsx`
- 关键调整：
  - 首屏和三张引导卡统一压缩成短句表达（同样信息，更少阅读负担）。
  - “这次会发生什么”区块改成更直接的动作承诺，减少解释腔。
  - 输入区说明和真实链路提示压短，避免重复强调。
  - 文本框 placeholder 改成更贴近当前产品场景的短示例。
  - 侧栏 `真流程` 从两块说明收成一块行动描述，减少重复。

### 2) Progress 页信息层级收紧

- 文件：`frontend/src/pages/ProgressPage.tsx`
- 关键调整：
  - 四个阶段描述改短，减少“技术解释味”。
  - `blocked_reason / next_action` 映射文案改成更短、更可执行。
  - 顶部描述与事实卡 help 文案压缩，保留结论和动作，不堆解释。
  - 保留“中途返回不丢描述”的关键承诺，避免用户焦虑。

### 3) report 示例态降权（避免“像 mock”）

- 文件：`frontend/src/lib/product-surface.ts`
- 关键调整：
  - `example` 数据源不再展示显眼 badge（避免和真实结果并列抢注意力）。
  - 仍保留明确 warning，但改成更短、直接、动作导向：
    - `当前不是实时结果`
    - `要看真流程，请从输入页重新发起一次真实分析`

## 验证结果

- 定向测试：
  - `cd frontend && npm run test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ProgressPage.test.tsx src/pages/__tests__/ReportPage.test.tsx`
  - 结果：`3 files passed / 17 tests passed`
- 完整正式 E2E：
  - `make test-e2e`
  - 结果：`21 passed`
- 构建验证：
  - `cd frontend && npm run build`
  - 结果：通过

## 当前结论

- 本轮属于“读感和信任感”补刀，不是扩功能。
- 主链稳定性未受影响（完整 E2E 继续全绿）。
- 交互理解成本下降、示例态干扰下降，产品完成感继续上移。

## 下一步

进入 Phase 26 收尾两项：

1. 桌面端 + 移动端截图级精品验收（五张关键页面全覆盖）。
2. 按 `ui-ux-pro-max / frontend-design / web-design-guidelines` 做最后一轮细修，重点看排版密度、首屏节奏和 CTA 视觉层级。
