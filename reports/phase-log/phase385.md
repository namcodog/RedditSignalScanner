# Phase 385 - 第四阶段产品抛光第一包：报告页 / hotpost / admin 首屏说人话

## 1. 发现了什么？

这一步不再继续第三轮那种“大修主链”，而是正式进入**产品抛光第一包**。

真正的问题不是系统没状态，而是：

- 后端已经有很多真实状态和数据范围字段
- 但前端首屏没有把这些话说给人听
- 结果就是：
  - 报告页一上来像“内容页”，不像“判断面板”
  - hotpost 结果页一上来像“快扫结果”，但没讲清它到底适不适合直接拍板
  - admin 首页像“统计页”，但没讲清它其实是系统驾驶舱，不是市场洞察页

大白话说：

- **机器已经稳了**
- **但用户第一眼还不够容易看懂**

所以这一步我没有再拆后端齿轮，而是直接收产品首屏。

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。  
改的是前端三张脸的首屏信息架构：

1. 报告页
2. hotpost 结果页
3. admin 首页

## 3. 精确修复方法？

这次不是修一个小文案，而是一整包一起做：

### 3.1 新增统一首屏组件

新增：

- [SurfaceHero.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/components/product/SurfaceHero.tsx)

这个组件统一承接 4 件事：

- 这页到底是什么
- 当前结果靠不靠谱
- 本次数据范围有多大
- 用户下一步应该先看什么

### 3.2 新增统一产品口径解释层

新增：

- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)

这里正式收了三套“说人话”的真相源：

- `buildReportSurfaceHero(...)`
- `buildHotpostSurfaceHero(...)`
- `buildAdminSurfaceHero(...)`

也就是说：

- 报告页不再自己瞎拼“这是一份什么报告”
- hotpost 不再自己瞎拼“这是实时还是缓存”
- admin 不再自己瞎拼“系统今天稳不稳”

### 3.3 三张脸一次性接入

落地页面：

- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)
- [HotPostResultPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostResultPage.tsx)
- [AdminDashboardPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/AdminDashboardPage.tsx)

现在首屏统一能讲清楚：

#### 报告页

- 这是正式深读 / 快速精简 / 侦察简报 / 受限结果
- 本次覆盖几个社区、处理多少帖子
- 结构化解读是否完整
- 当前更应该先看商业机会、痛点还是市场健康度

#### hotpost 结果页

- 这是热点快报 / 痛点快扫 / 机会快扫
- 当前是实时结果 / 缓存结果 / 回退结果
- 样本够不够
- 这次更适合先快速判断，还是已经值得继续生成深度报告

#### admin 首页

- 这页不是看市场结论，是看系统今天跑得稳不稳
- 活跃节点、缓存命中、今日完成任务直接讲清楚
- 新人一眼就知道先看系统、再看社区、再看任务账本

### 3.4 测试一起锁住

新增 / 更新：

- [ReportPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/ReportPage.test.tsx)
- [AdminDashboardPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/AdminDashboardPage.test.tsx)
- [HotPostResultPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/__tests__/HotPostResultPage.test.tsx)

现在至少锁住了这三件事：

- 报告页会明确说“这是一份什么报告”
- hotpost 会明确说“这是一份什么快扫”
- admin 会明确说“这是系统驾驶舱”

## 4. 验证结果

### 4.1 前端定向回归

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx \
  src/pages/hotpost/__tests__/HotPostResultPage.test.tsx \
  src/pages/__tests__/ReportFlow.integration.test.tsx
```

结果：

- `4 passed`

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

### 4.4 剩余注意点

这次测试里还看到两类**非阻塞 warning**：

- `baseline-browser-mapping` 过期提醒
- 现有测试环境里一个 `React.jsx type is invalid` 的旧 warning

这两条没有导致本轮失败，也不是这次产品抛光引入的新断点。  
我这次没有把它们混成主线故障。

## 5. 下一步系统性的计划是什么？

第四阶段现在已经不是“准备开始”，而是**第一包已经落地**。

接下来我建议继续按“大包封板”走：

1. **报告 / hotpost / admin 的第二包**
   - 统一空状态、降级状态、下一步 CTA
   - 把“可信度 + 数据范围 + 行动建议”继续收紧

2. **用户侧命名和文档同步**
   - README
   - 页面标题
   - 导航命名
   - 让产品外部说法彻底统一

3. **第四阶段总复盘**
   - 判断当前系统是否已经从“95+ 稳定机器”进一步进入“更像成品”的状态

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方不是“页面更漂亮了”，而是：

- **三张最重要的脸终于开始说人话了**

现在系统不只是“工程上修到位”，而是已经开始对外讲清楚：

- 这是什么结果
- 这次结果靠不靠谱
- 数据范围有多大
- 用户下一步该干嘛

如果再用最直白的话总结：

- **第三轮把机器修稳了**
- **这一步开始把机器变成更像产品的成品**
