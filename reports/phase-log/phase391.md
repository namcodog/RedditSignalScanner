# Phase 391 - 第四轮产品打磨第一包：首屏价值压缩

## 1. 发现了什么？

`phase390` 定完方向后，这一包只盯一个目标：

- 把三张脸的首屏从“解释型”再往前推一格
- 收成更像“拍板型”的判断页

这次照出来的核心问题是：

1. 报告页虽然已经能说人话，但首屏还偏“说明书口气”
   - 更像在解释这页是什么
   - 还不够像在直接告诉用户“这次值不值得继续做”

2. hotpost 首屏虽然已经不刺耳，但判断力还不够硬
   - 更像“方向提示”
   - 还不够像“这波现在追不追”

3. admin 首屏虽然已经开始像驾驶舱，但标题还偏“系统描述”
   - 还不够像一个可行动判断：
     - 今天能不能放心开工

大白话说：

- **上一包让用户能看懂**
- **这一包要让用户更快拍第一板**

## 2. 是否需要修复？

需要，而且这包已经修完。

这次没有改数据结构，没有改 API，没有改后端逻辑。  
只改首屏判断层：

- report hero / 决策摘要
- hotpost hero / 决策摘要
- admin hero
- 对应前端测试口径

## 3. 精确修复方法？

### 3.1 报告页

更新：

- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)
- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)

收口结果：

- 首屏标题：
  - `这份结果已经可以直接看结论`
  - 改成：
  - `这次已经值得继续做`
- 决策面标题：
  - `先做判断，再决定要不要继续深挖`
  - 改成：
  - `先拍第一板，再决定投多少时间`
- 主 verdict：
  - `可以继续往正式判断推进`
  - 改成：
  - `值得继续推进`

同时把首屏 next steps 压短，减少解释感，增强拍板感。

### 3.2 hotpost

更新：

- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)
- [HotPostResultPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostResultPage.tsx)

收口结果：

- 首屏标题：
  - `这波已经够你先判断方向`
  - 改成：
  - `这波先决定追不追`
- 决策面标题：
  - `先判断值不值得追，再决定要不要转深度报告`
  - 改成：
  - `先决定追不追，再转深度报告`
- 主 verdict：
  - `这波值得先追一轮`
  - 改成：
  - `先追一轮再拍板`

方向更明确：

- 不是在提示
- 是在催用户做第一层动作判断

### 3.3 admin

更新：

- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)

收口结果：

- 首屏标题：
  - `今天这套机器整体是稳的`
  - 改成：
  - `今天可以放心开工`
- 首屏描述：
  - 改成更直接的：
  - `这里不回答市场值不值，只回答今天这套机器能不能放心开工。`

这让 admin 更像驾驶舱，而不是统计页。

### 3.4 测试先行并同步更新

更新：

- [ReportPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/ReportPage.test.tsx)
- [ReportFlow.integration.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/ReportFlow.integration.test.tsx)
- [HotPostResultPage.surface.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx)
- [AdminDashboardPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/AdminDashboardPage.test.tsx)

这次先改测试口径，再收实现。

## 4. 验证结果

### 4.1 前端定向测试

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx \
  src/pages/__tests__/ReportFlow.integration.test.tsx
```

结果：

- `4 passed`
- `9 passed`

### 4.2 前端构建

```bash
cd frontend && npm run build
```

结果：

- 构建通过

### 4.3 非阻塞提醒

仍有两类旧提醒：

- `baseline-browser-mapping` 过期提示
- `React.jsx type is invalid` 的现存 warning

这两条不是本次引入的新问题，也没有挡住测试和构建。

## 5. 下一步系统性的计划是什么？

下一包直接进入 `Phase 392`：

- CTA 动作闭环统一

重点只做三件事：

1. 主 CTA 统一
   - 深挖
   - 看证据
   - 返回重跑

2. 次 CTA 统一
   - 逐维探索
   - 回输入页 / 搜索页
   - 去控制面

3. 返回后的带回提示统一
   - query
   - product description
   - 当前上下文说明

## 6. 这次执行的价值是什么？达到了什么目的？

这包最值钱的，不是文案变短了，而是：

- **首屏开始更像“判断页”而不是“说明页”**

现在三张脸更接近：

- report：这次值不值得继续做
- hotpost：这波追不追
- admin：今天能不能放心开工

一句大白话收口：

- **Phase 391 已经把首屏从“能懂”往“能拍板”推进了一大步。**
