# Phase 413 - Hotpost 默认视图去噪收口（2026-03-19）

## 目标
- 完成 Phase 23 最后一项：让 live hotpost 结果页默认只展示当前决策必要信息，减少信息过载。

## 改动

### 1) 默认只看决策主链
- 文件：`frontend/src/pages/hotpost/HotPostResultPage.tsx`
- 新增：
  - `showAdvancedInsights` 状态
  - `hasAdvancedInsights` 检测
  - 新区块 `补充细节（可选）`
- 行为变化：
  - `rant/opportunity` 的补充板块（痛点细分、竞品、迁移、用户分层、工具清单）改为默认折叠
  - 用户手动点击 `展开补充细节` 才显示
  - 默认视图保留：结论、三步节奏、关键证据帖、主要社区、CTA

### 2) 测试同步
- 文件：`frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`
- 断言从“默认看到用户细分块”改为：
  - 默认看到 `补充细节（可选）` 与 `展开补充细节`
  - 默认看不到 `用户现在缺什么`

## 验证

```bash
cd frontend && npm run test -- src/pages/__tests__/HotPostResultPage.surface.test.tsx src/pages/__tests__/ReportPage.test.tsx
```
- 结果：`9 passed`

```bash
make test-e2e
```
- 结果：`21 passed`

```bash
cd frontend && npm run build
```
- 结果：通过

## 结论
- `Phase 23` 已全部完成。
- hotpost 默认视图已从“信息堆叠”收成“决策主链优先”，符合“只展示当前真的有用的信息”。
- 下一步进入 `Phase 24`：补齐 Input / Progress 全链路体验地图。
