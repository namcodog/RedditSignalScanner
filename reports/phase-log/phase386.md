# Phase 386 - 第四阶段产品抛光第二包：三张脸的空状态 / 降级状态 / 下一步动作统一

## 1. 发现了什么？

这一步真正的问题不是页面没有状态，而是：

- 报告页、hotpost、admin 三张脸都已经有真实状态
- 但空状态、错误状态、降级状态还是各说各话
- 有的只是一个红字
- 有的只是“暂无数据”
- 有的有按钮，有的没有下一步

大白话说：

- **机器已经稳了**
- **但用户遇到“这次结果不够满、暂时没结果、这页出错了”时，还是会愣一下**

另外这次还顺手照出一个真口子：

- `src/pages/hotpost/__tests__/HotPostResultPage.test.tsx` 放在当前 vitest 默认 include 规则外面
- 之前这张脸的测试其实没有真的被默认收进去
- 我这次顺手补成了一个真正会跑的页面测试

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。  
改的是：

1. 统一状态面板组件
2. SurfaceHero 的降级提醒表达
3. 报告页 / hotpost / admin 三张脸的错误态、空态和下一步动作
4. 对应前端测试

## 3. 精确修复方法？

### 3.1 新增统一状态面板

新增：

- [ProductStatePanel.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/components/product/ProductStatePanel.tsx)

统一承接三类状态：

- `empty`
- `degraded`
- `error`

并统一支持：

- 标题
- 解释
- 下一步提示
- 1-2 个 CTA

### 3.2 统一三张脸的降级表达

更新：

- [SurfaceHero.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/components/product/SurfaceHero.tsx)
- [product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)

现在三张脸只要有 warning，不再是简单一条黄底提示，而是统一走降级状态面板。

补了：

- `warningTitle`
- `warningNextStep`

也就是说：

- 报告页的“不是满配结果”
- hotpost 的“降级或回退结果”
- admin 的“系统今天有提醒”

都开始用同一套状态语义说话。

### 3.3 报告页

更新：

- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)

这次统一了：

- 报告加载失败的整页错误态
- 痛点证据缺失时的空状态

现在不是简单一条报错或“暂无证据”，而是明确说：

- 现在发生了什么
- 为什么先不要急着拍板
- 你下一步应该做什么

### 3.4 hotpost 结果页

更新：

- [HotPostResultPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostResultPage.tsx)

这次统一了：

- 快扫失败时的整页错误态
- `Top Evidence` 为空时的空状态
- 社区列表为空时的空状态

现在 hotpost 不再只会说“暂无帖子显示”，而会明确告诉用户：

- 这次是没筛出代表性帖子
- 还是这波信号根本没拿稳
- 下一步该继续深挖，还是先回去换关键词

### 3.5 admin 首页

更新：

- [AdminDashboardPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/AdminDashboardPage.tsx)

这次统一了：

- 驾驶舱加载失败的错误态
- 最近任务为空的空状态
- 没拿到 stats 时的兜底空状态

现在 admin 不再只是：

- `错误: xxx`
- `暂无最近任务`

而是明确说：

- 系统现在怎么了
- 这是不是坏了
- 应该先去任务账本还是先去社区池

### 3.6 测试一起锁住

更新 / 新增：

- [ReportPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/ReportPage.test.tsx)
- [AdminDashboardPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/AdminDashboardPage.test.tsx)
- [HotPostResultPage.surface.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx)

这次顺手把 hotpost 旧测试“默认不被 vitest 收进去”的口子补平了。

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

### 4.4 非阻塞提醒

仍然能看到两类旧 warning：

- `baseline-browser-mapping` 版本过旧提醒
- 一个现存的 `React.jsx type is invalid` warning

它们都不是这次改动引入的新断点，也没有挡住测试和构建。

## 5. 下一步系统性的计划是什么？

第四阶段第二包已经落地。

接下来继续按“大包封板”走：

1. **用户侧命名和动作文案统一**
   - 页面标题
   - 按钮文案
   - README / 外部叙事

2. **报告页、hotpost、admin 的 CTA 再收一轮**
   - 让“看结果 / 深挖 / 返回搜索 / 去控制面”更一致

3. **第四阶段总复盘**
   - 判断当前系统是否已经从 `95+` 稳定机器，进一步变成“更像成品”的状态

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方不是“加了一个状态组件”，而是：

- **三张最重要的脸，终于开始在“没结果 / 结果不够满 / 这页出错了”时，说同一种人话了**

现在用户遇到状态问题，不再只看到：

- 没数据
- 错误
- 暂无

而是能直接知道：

1. 现在发生了什么
2. 这次结果靠不靠谱
3. 下一步该怎么走

一句大白话收口：

- **第四阶段第二包已经把三张产品面的状态表达真正拉平了，产品开始更像成品，而不是一组功能页。**
