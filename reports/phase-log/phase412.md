# Phase 412 - Hotpost 快扫体验重构（第一批，2026-03-19）

## 本轮目标
- 把 Hotpost 首屏继续从“解释”收成“追不追判断”。
- 压缩快扫中段文字密度，强化“摘要 → 证据 → 社区”的三步节奏。
- 确保改动后正式 E2E 仍全绿。

## 关键改动

### 1) 首屏 verdict 与理由压短
- 文件：`frontend/src/lib/product-surface.ts`
- 主要变化：
  - `先追一轮再拍板` → `先定追不追`
  - `这次快扫已经够你先做判断。` → `这次快扫已经够你先拍板。`
  - `觉得这波值钱，就直接转深度报告。` → `值钱就继续深挖。`
  - 二级理由改为更短句：
    - `同一需求在重复出现，值得继续追。`
    - `抱怨已经开始聚焦，值得判断是不是稳定痛点。`
    - `话题已经开始集中，值得判断是真热还是短噪音。`
  - Action Plan 文案同步压短（保留原动作结构）。

### 2) 快扫中段引导压短
- 文件：`frontend/src/pages/hotpost/HotPostResultPage.tsx`
- 主要变化：
  - `别全读。先看摘要，再扫证据，最后盯社区，看这波是真机会还是短噪音。`
  - 改为：`先看摘要，再扫证据，最后盯社区。`

### 3) 测试断言同步
- 文件：
  - `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`
  - `frontend/src/pages/__tests__/ReportPage.test.tsx`（承接 Phase 411）
  - `frontend/e2e/performance.spec.ts`
  - `frontend/e2e/product-polish-smoke.spec.ts`
- 主要变化：
  - 同步新文案断言，避免“页面改了、验收还在旧文案”。

## 验证结果

### 定向页面测试
```bash
cd frontend && npm run test -- src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/HotPostResultPage.surface.test.tsx
```
- 结果：`9 passed`

### 正式 E2E
```bash
make test-e2e
```
- 结果：`21 passed`

### 前端构建
```bash
cd frontend && npm run build
```
- 结果：通过

## 当前阶段结论
- `Phase 23` 已完成前三项（首屏追不追判断、三步阅读顺序、动作链一致性）。
- 剩余一项：继续清理 live hotpost 结果页里“可删的解释性块”，只保留当前用户决策需要的信息。
