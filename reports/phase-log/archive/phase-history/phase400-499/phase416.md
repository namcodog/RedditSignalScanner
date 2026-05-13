# Phase 416 - Admin 信任面重构（第一批，2026-03-19）

## 目标
- 推进 Phase 25：让 Admin 页不再只是展示指标，而是直接告诉用户“今天风险几级、该先做什么”。

## 关键改动

### 1) 风险级别显式化
- 文件：`frontend/src/pages/AdminDashboardPage.tsx`
- 新增风险判定：
  - `high`: 无活跃 worker
  - `medium`: cache hit rate < 0.3
  - `low`: 其余情况
- 新增可读输出：
  - `当前风险级别`（高/中/低）
  - 颜色编码（红/橙/绿）

### 2) 今日建议动作显式化
- 文件：`frontend/src/pages/AdminDashboardPage.tsx`
- 新增区块：
  - `今日建议动作`
  - 根据风险给一句可执行建议，避免用户自己翻译指标。

### 3) 测试同步
- 文件：`frontend/src/pages/__tests__/AdminDashboardPage.test.tsx`
- 新增断言：
  - `当前风险级别`
  - `低风险`
  - `今日建议动作`
  - 对应建议文案

## 验证

```bash
cd frontend && npm run test -- src/pages/__tests__/AdminDashboardPage.test.tsx src/pages/__tests__/ProgressPage.test.tsx src/pages/__tests__/InputPage.test.tsx
```
- 结果：`17 passed`

```bash
make test-e2e
```
- 结果：`21 passed`

```bash
cd frontend && npm run build
```
- 结果：通过

## 当前结论
- Phase 25 前两项已完成（信任面表达、风险+建议动作）。
- 下一步继续收口：
  - 任务账本 / 社区池 / 队列状态的“决策化表达”
  - admin 异常态、空态、成功态的最后一轮统一。
