# Phase 393 - 三张脸成品感统一

## 本轮目标

把 report、hotpost、admin 三张脸继续往“同一套成熟产品”收一格。

这轮不碰后端能力，也不重做信息架构，只收三类东西：

1. 页面标题和区块命名
2. 下半屏继续阅读的节奏
3. admin 的后台味

## 完成情况

### 1. admin 从后台页口气收回产品口气

- 顶部主标题从 `Admin 仪表盘` 改成 `系统控制面`
- 补了一句更像产品的说明：先确认今天机器稳不稳，再决定要不要继续开新任务
- 三个关键区块重新命名：
  - `今天先看什么`
  - `今天机器稳不稳`
  - `控制面捷径`
- `查看全部` 改成 `看全部任务`

这样 admin 不再像一个独立后台，而更像整个产品里的控制面。

### 2. report 的“继续往下看”节奏收紧

- 把旧的“完整报告已经准备好，先看判断，再决定要不要往下读完”收成 `继续拆这次判断`
- 把说明收成更符合实际用户节奏的话：
  - 先从最想确认的一块往下看
  - 别把五个维度一次性全塞给自己

这一步的作用，是把 report 下半屏从“功能入口”变成“阅读节奏引导”。

### 3. hotpost 的下半屏命名和节奏对齐

- `继续看细节` 改成 `继续拆这波判断`
- 增加一段节奏提示，告诉用户先看摘要、证据、社区分布
- `热门讨论 (Top Evidence)` 改成 `关键证据帖`
- `涉及社区` 改成 `这波主要出在哪些社区`

这会让 hotpost 跟 report 的节奏更接近，不再像一个快扫页、一个深读页各说各话。

## 验证结果

已通过：

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx
```

结果：
- `3 files passed / 11 tests passed`

已通过：

```bash
cd frontend && npm run build
```

## 关键改动文件

- `frontend/src/lib/product-surface.ts`
- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- `frontend/src/pages/__tests__/AdminDashboardPage.test.tsx`
- `frontend/src/pages/__tests__/ReportPage.test.tsx`
- `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`

## 产品判断

这轮的价值，不是“页面更花”，而是“三张脸终于更像同一家公司做出来的”。

现在更统一的是：

- 都先讲判断，再讲细节
- 都用更像产品的话来命名区块
- 都在告诉用户“先看哪、再看哪”

这会明显抬高完成感。

## 遗留提醒

当前还有两个旧提醒，不阻塞本轮验收：

- `baseline-browser-mapping` 版本过期 warning
- 现有 `React.jsx type is invalid` warning，仍指向 `index.tsx`

## 下一步

进入 `Phase 394`：

- 用真实样本做一轮更严格的成品验收
- 检查强结果 / 弱结果 / 快扫结果的节奏是否已经稳定
- 为最终冲 95 分做总复盘和补刀清单
