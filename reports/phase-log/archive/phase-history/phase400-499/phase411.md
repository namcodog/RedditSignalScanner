# Phase 411 - Report 页价值 punchline 重构收口（2026-03-19）

## 本轮目标
- 把 Report 首屏和中段进一步收成“结论 / 证据 / 下一步”，减少解释性文案和阅读负担。
- 确保正式 E2E 口径与新文案同步，不再出现“页面已改、验收还在旧世界”的错配。

## 关键改动

### 1) 首屏决策表达更硬
- 文件：`frontend/src/lib/product-surface.ts`
- 主要收口：
  - `verdictTitle` 从“值得继续推进”改为“可以拍第一板”。
  - 弱结果口径从“先判断值不值得追”收成“先定值不值得追”。
  - 下一步文案压短为“先挑最影响拍板的一块看。”
  - fallback reasons 改成更直接的证据话术（持续冒头 / 抱怨可解）。

### 2) 中段从“看信号”改成“拍板证据”
- 文件：`frontend/src/pages/ReportPage.tsx`
- 主要收口：
  - `DecisionSummaryPanel` 顶部标题改为：
    - 强结果：`先拍第一板`
    - 弱结果：`这轮先拍小板`
  - reasons 区统一标题：`拍板依据`
  - 中段主标题改为：`支持拍板的 3 条证据`
  - 中段副文案改为：`先扫这三条就够；不够再往下拆。`
  - selector 标题改为：`继续拆证据`

### 3) 验收链同步到新文案
- 单测文件：
  - `frontend/src/pages/__tests__/ReportPage.test.tsx`
- E2E 文件：
  - `frontend/e2e/performance.spec.ts`
  - `frontend/e2e/product-polish-smoke.spec.ts`
- 修复内容：
  - 把旧断言（如“先看这 3 个信号”“继续拆这次判断”）统一升级到新口径。

## 验证结果

### 前端单测
```bash
cd frontend && npm run test -- src/pages/__tests__/ReportPage.test.tsx
```
- 结果：`4 passed`

### 前端构建
```bash
cd frontend && npm run build
```
- 结果：通过

### 正式 E2E
```bash
make test-e2e
```
- 首次结果：`2 failed / 18 passed / 1 did not run`
  - 根因：E2E 仍断言旧文案，不是功能回归。
- 同步更新 E2E 断言后复跑：
  - 结果：`21 passed`

## 本轮结论
- Phase 22 可判定完成。
- 当前 report 页第一屏已更接近“10 秒看懂值不值”的产品目标。
- 下一阶段进入 Phase 23：继续收 hotpost 快扫链路（追不追判断、三步节奏、返回链一致性）。
