# Phase 414 - Input/Progress 体验地图补齐（第一批，2026-03-19）

## 本轮目标
- 推进 Phase 24：把输入页与等待页的“预期管理 + 返回链”收齐，减少用户中途迷路。

## 关键改动

### 1) Input 首屏补齐结果预期
- 文件：`frontend/src/pages/InputPage.tsx`
- 新增“这轮可能出现的 3 种状态”卡片：
  - 可能直接出完整结论
  - 也可能先给方向判断
  - 中途返回不丢方向
- 同时细化 prefill 标题：
  - `restart-analysis` 来源显示为 `已带回这次待优化方向`

### 2) Progress 页补齐返回链
- 文件：`frontend/src/pages/ProgressPage.tsx`
- 新增 `navigateBackToInput()`，统一把当前产品描述带回输入页（`prefillSource=restart-analysis`）。
- 应用场景：
  - 取消分析确认后返回输入页，不再丢描述
  - 错误态主 CTA 从“回首页”改成“回输入页重跑”
  - warmup/auto-rerun 状态新增“回输入页重跑”按钮
- 运行提示增加明确说明：
  - “中途返回不会丢掉你刚才的产品描述，系统会自动带回输入页。”

### 3) 测试同步
- 文件：
  - `frontend/src/pages/__tests__/InputPage.test.tsx`
  - `frontend/src/pages/__tests__/ProgressPage.test.tsx`
- 补充断言：
  - Input 首屏预期卡
  - Progress 返回链文案与“回输入页重跑”按钮

## 验证结果

```bash
cd frontend && npm run test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ProgressPage.test.tsx src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/HotPostResultPage.surface.test.tsx
```
- 结果：`20 passed`

```bash
make test-e2e
```
- 结果：`21 passed`

```bash
cd frontend && npm run build
```
- 结果：通过

## 当前结论
- Phase 24 已完成第一批核心收口（输入预期、等待解释、返回不丢描述）。
- 剩余项：把“8 条核心路径”做成正式体验地图并固化到验收文档。
