# Phase 387 - 第四阶段产品抛光第三包：用户面结果等级收口

## 1. 发现了什么？

这一步真正的问题不是“前端没状态”，而是：

- 我们已经把系统修稳了
- 但用户面还会直接漏出后台口气

最典型的就是这些说法：

- 数据不足
- 暂无摘要 / 暂无描述 / 暂无引用
- 结果不够满
- 这次失败了 / 这次没拿到可用结果

大白话说：

- **工程上这是在说真话**
- **产品上这会让用户以为我们产品不行、数据不行、算法不行**

这一步要解决的，不是把真相藏起来，而是：

- **把后台状态翻译成用户可行动的状态**

统一口径变成三档：

1. 可直接看结论
2. 先判断方向
3. 系统正在补充更多证据

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。  
改的是：

1. 报告页用户面结果等级表达
2. hotpost 结果页用户面结果等级表达
3. 共享产品文案层
4. 对应前端测试

## 3. 精确修复方法？

### 3.1 共享产品层

更新：

- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)

这次做了三件事：

1. 把 `report_tier` 的对外说法收成：
   - `完整结论`
   - `方向判断`
   - `线索预览`
2. 把 hotpost 的来源和信号表达收成：
   - `刚刚扫描`
   - `最近一次扫描`
   - `快速整理结果`
   - `信号扎实 / 方向已浮现 / 先看线索 / 正在补证据`
3. 把 admin 空闲态从 `暂无` 收成 `暂时空闲`

大白话说：

- **共享产品层现在开始统一说“用户听得懂的话”**

### 3.2 报告页

更新：

- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)

这次把整组用户面表达一起收了：

1. 维度卡片空态
   - 不再说“数据不足”
   - 改成：
     - 先判断方向
     - 继续深挖时补齐

2. 整页错误态
   - 不再直接把 raw error 端给用户
   - 改成：
     - `这份结果还在整理中`
     - `系统刚才没把这份结果整理完整...`

3. 证据缺链接时的提示
   - 不再说：
     - `数据不足，暂无原帖链接`
   - 改成：
     - `这条原话已经保留下来，原帖跳转会在继续深挖时自动补齐`

4. 证据区空态
   - 不再说“没有证据”
   - 改成：
     - `先看结论和解读就够了`

5. HTML 报告入口兜底
   - 不再 alert：
     - `暂无完整 HTML 报告`
   - 改成：
     - `完整报告还在整理中，先看上面的决策卡和结论就够了。`

### 3.3 hotpost 结果页

更新：

- [HotPostResultPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostResultPage.tsx)

这次把整组用户面表达一起收了：

1. 整页错误态
   - 不再说：
     - `这次快扫还没拿到可用结果`
     - `获取结果失败 / 请求失败`
   - 改成：
     - `这次快扫还在整理中`
     - `系统已经接到这次搜索，现在正在重新整理这波热点信号...`

2. Header 来源文案
   - `From Cache / Live Search`
   - 改成：
     - `最近一次扫描 / 刚刚扫描`

3. 摘要兜底
   - 不再说：
     - `暂无摘要`
   - 改成：
     - `这次快扫已经先把方向捞出来了，系统会继续补一段更完整的摘要。`

4. 痛点卡片兜底
   - 不再说：
     - `暂无描述 / 暂无引用`
   - 改成：
     - `先把这类用户声音当成一个方向判断...`
     - `这类原话会在继续深挖时自动补齐。`

5. Top Evidence 空态
   - 改成：
     - `先看摘要和机会点就够了`

6. 社区列表空态
   - 改成：
     - `先顺着这波趋势判断方向`

7. 深度报告失败 alert
   - 不再直接把 raw error 暴露给用户
   - 改成：
     - `系统刚才没把深度报告接上，先稍后再试一次。`

### 3.4 测试一起锁住

更新：

- [ReportPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/ReportPage.test.tsx)
- [HotPostResultPage.surface.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx)

这次重点锁住的是：

1. 报告页首屏现在说：
   - `这份结果已经可以直接看结论`
2. 报告失败时不再把 raw backend 错误直接端给用户
3. hotpost 首屏现在说：
   - `这波信号更适合先探方向`
4. hotpost 失败时不再把 raw backend 错误直接端给用户

## 4. 验证结果

### 4.1 前端定向回归

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx
```

结果：

- `8 passed`

### 4.2 前端构建

```bash
cd frontend && npm run build
```

结果：

- 构建通过

### 4.3 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.4 额外检查

用关键词扫过这 3 个核心文件：

- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)
- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)
- [HotPostResultPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostResultPage.tsx)

确认这一包已经去掉这些直伤观感的词：

- `数据不足`
- `结果不够满`
- `分析不到位`
- `受限结果`
- `回退结果`
- `暂无摘要 / 描述 / 引用`
- `获取结果失败 / 请求失败`

## 5. 下一步系统性的计划是什么？

第四阶段第三包已经落地。

接下来继续按“大包封板”走最后两步：

1. **产品动作和 CTA 统一**
   - 报告页
   - hotpost
   - admin
   - README / 导航 / 按钮文案

2. **第四阶段总复盘**
   - 判断当前系统是否已经从 `95+` 稳定机器，进一步走到了“像成品”的状态

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方，不是改了几句文案，而是：

- **用户面不再把系统内部的短板感直接端出来了**

现在用户看到的是：

1. 这次能不能直接看结论
2. 这次更适合先判断方向
3. 这次系统还在补更多证据

而不是：

- 数据不够
- 结果不够满
- 分析失败
- 算法没跑好

一句大白话收口：

- **第四阶段第三包已经把“后台状态”翻译成了“用户可行动状态”，这一步做完，产品观感又顺了一大截。**
