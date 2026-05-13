# Phase 397 - 最后一层精品化微调：等待态也像产品

## 本轮目标

快速收掉最后一层“手感掉分点”：

- report 加载时不要只是骨架
- hotpost 等待时不要只是 spinner

用户在结果还没出来的时候，也应该感觉自己还在一条明确的产品路径里，而不是掉回通用加载页。

## 完成情况

### 1. report 骨架屏已经开始讲产品语言

这轮把 report 的 skeleton 顶部收成了更像产品的整理态：

- 标题：`正在整理这次判断`
- 说明：`先帮你把市场温度、用户抱怨和可追机会捞出来，马上就能进正式判断。`
- 辅助步骤：
  - `市场温度`
  - `用户抱怨`
  - `可追机会`

这样 report 在等待时，不再只是“页面还没出来”，而是在告诉用户系统正在把哪几块判断先整理出来。

### 2. hotpost 等待页不再像通用加载页

这轮把 hotpost 的 loading state 从：

- 一个 spinner
- 一句 `正在扫描 Reddit 社区...`

收成更像产品的等待态：

- 标题：`这波热点正在成型`
- 说明：`系统先帮你捞摘要、证据和社区，通常很快就能进入快扫判断。`
- 三步提示：
  - `先抓摘要`
  - `再抓证据`
  - `最后看社区`

这一步很小，但会直接抬高完成感。用户等待时也知道系统正在做什么，而不是只能盯着一个转圈。

## 验证结果

已通过：

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx
```

结果：
- `2 files passed / 9 tests passed`

已通过：

```bash
cd frontend && npm run build
```

## 关键改动文件

- `frontend/src/components/SkeletonLoader.tsx`
- `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- `frontend/src/pages/__tests__/ReportPage.test.tsx`
- `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`

## 当前判断

这轮做完后，我会把当前产品体感从 `Phase 396` 的约 `91`，再往上调到：

- `92`

这次抬分不靠大改，而是靠一件很典型的成品事：

- 等待过程也终于不像半成品了

## 当前仍未到 95 的原因

现在离 95 分还差的，基本只剩最后一层精品感：

- 更细的加载到结果过渡
- 视觉主次再压一层
- 把几个旧 warning 清掉，减少“这还是开发中”的味道

## 下一步

进入 `Phase 398`：

1. 做最终重打分
2. 明确离 `95` 还差的最后几刀
3. 判断是继续冲，还是先以 `92` 左右作为当前阶段验收点
