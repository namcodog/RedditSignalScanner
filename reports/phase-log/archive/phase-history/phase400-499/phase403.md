# Phase 403 - 首轮入口与 Admin 外壳精品化

## 背景

`Phase 402` 已经把三张关键结果页和正式 E2E 收到了约 `94-95` 分，但离 `98` 还差最后一层明显断点：

- `InputPage` 还是旧输入页味道
- `ProgressPage` 还是功能等待页味道
- `AdminLayout / AdminRoute` 还残留旧后台外壳

这轮目标不是再加新能力，而是把：

- 第一次进入产品的第一眼
- 分析等待过程的手感
- admin 体系的整体壳子

一起拉进同一套高完成度视觉系统，并确认真链路没有被带坏。

---

## 本轮发现

### 1. 离 98 分最大的拖分项，确实就是首轮入口和 admin 外壳

在 `Phase 402` 后，结果页已经开始像成熟产品，但用户第一次进来和等待结果时，还是会掉回“普通工具页”的感觉：

- 输入页还停在旧 header、旧表单卡、旧 CTA 语言
- 等待页还像“技术流程页”，没有把系统在做什么讲得足够像产品
- admin 外壳还是传统 sidebar 后台样式，和新视觉系统明显断层

结论：

- 这轮不该再改 report / hotpost 主体
- 该直接收第一轮入口和 admin 壳子

### 2. 等待页除了视觉问题，还有真实状态表达没收透

`ProgressPage` 除了旧样式，还存在一个产品完成感问题：

- warmup / auto rerun 这类“还没出正式结论”的状态，没有讲清楚“现在卡在哪、系统下一步会做什么”

这会直接影响用户对系统可信度的判断。

结论：

- 这轮必须把等待页的卡点说明一起产品化

### 3. 这轮如果只改单测，不跑正式 E2E，分数会再被高估

因为这次动的是：

- 输入页提交链路
- 等待页 SSE / 轮询页
- admin 壳子

它们都属于正式 E2E 里的真主链。

结论：

- 这轮必须跑构建 + 定向 vitest + `make test-e2e`

---

## 本轮执行

### A. 补共享基础样式，避免四个文件各写一套

主要改动：

- `frontend/src/styles/index.css`

具体落地：

- 新增 `surface-field`
- 新增 `surface-admin-shell`
- 新增 `surface-admin-link / surface-admin-link-active`

这一步的价值是先把基础语言补出来，避免继续在页面里堆散乱 utility class。

### B. 重做 InputPage，让第一眼就像成品入口

主要改动：

- `frontend/src/pages/InputPage.tsx`

具体落地：

- 头部切进统一品牌壳层
- 首屏改成更像“把方向交给系统判断”的封面
- 表单区域改成主输入面板 + 右侧辅助说明
- 示例卡和“接下来会发生什么”一起进入统一 surface 语言
- 保留原有主链关键文案与按钮名，避免测试和用户习惯断掉

### C. 重做 ProgressPage，让等待过程也像产品

主要改动：

- `frontend/src/pages/ProgressPage.tsx`

具体落地：

- 顶部切到统一品牌壳层
- 首屏改成更像“分析正在进行中的驾驶卡”
- 保留 `正在分析您的产品 / 正在分析的产品 / 分析进度` 这些正式验收锚点
- warmup / auto rerun 状态新增四块说明：
  - `阶段`
  - `卡点原因`
  - `下一步`
  - `预计重试`
- 取消分析不再用浏览器原生 `confirm`，而是改成页内确认面板

### D. 重做 AdminLayout / AdminRoute，清掉旧后台味

主要改动：

- `frontend/src/components/AdminLayout.tsx`
- `frontend/src/components/AdminRoute.tsx`

具体落地：

- Admin sidebar 全量切进新控制台视觉
- 删除 emoji 导航
- 用真实产品命名重组导航分区：控制面 / 社区流转 / 任务追踪
- AdminRoute loading 和 forbidden 状态统一进产品态面板，不再用旧 inline style 英文页

---

## 验证结果

### 定向前端测试

- `cd frontend && npx vitest run src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ProgressPage.test.tsx src/components/__tests__/AdminLayout.test.tsx src/pages/__tests__/AdminDashboardPage.test.tsx`
- 结果：`4 files passed / 14 tests passed`

### 构建验证

- `cd frontend && npm run build`
- 结果：通过

### 正式 E2E

- `make test-e2e`
- 结果：`21 passed`

---

## 当前判断

按现在的产品标准，这套产品可以从 `Phase 402` 的约 `94-95`，进一步抬到约 `96-97`。

为什么能上这一档：

- 第一次进入产品的第一眼终于不掉档了
- 等待态不再像技术页面
- admin 体系终于不再像旧后台外挂在产品外面
- 正式 E2E 也证明这轮不是只在视觉层自嗨

但我还不直接给 `98`，因为最后还差两件事：

- 桌面端 / 移动端的截图级精品验收还没完整跑
- 还有最后一层细碎的视觉密度、留白和过渡微调空间

---

## 下一步建议

直接开 `Phase 404`，只做最后一轮冲 `98`：

1. 做桌面端 + 移动端截图级精品验收
2. 只记录截图里还会掉完成感的细碎问题
3. 小范围修留白、节奏、密度、动效
4. 重跑 `make test-e2e`
5. 最后再重打一次分

---

## 本轮价值

这轮最值钱的，不是“又改了四个文件”。

真正的价值是：

- 产品从“结果页像成品”推进到“第一步、等待中、后台壳子都像成品”

一句大白话收口：

- 现在不只是结果页能打人了
- 连入口和等待过程，也开始像一套值得信任的成熟产品了
