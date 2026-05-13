# Phase 447 - 去掉标准导览中间页，首页标准卡直达标准报告

## 发现了什么？

- 用户在真实前端验收里继续指出一个对的判断：
  - `standard-case` 这层“标准导览 / 导航页”已经没有独立价值
  - 它和标准报告详情页承载的是重复信息
  - 多这一层只会增加一次点击和一层认知负担
- 当前真正合理的主链应该是：
  - 首页 6 张标准卡
  - 直接进入标准报告页
  - 旧 `/standard-case/:slug` 只保留兼容跳转，不再停留

## 是否需要修复？

- 需要，而且应该立刻收掉。
- 这不是“文案优化”，而是把一层已经失去价值的中间结构从真实流程里移除。

## 精确修复方法

### 1. 标准导览页改成纯跳转壳

- 文件：[StandardCasePage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/StandardCasePage.tsx)
- 处理：
  - 页面不再渲染任何内容
  - 进入 `/standard-case/:slug` 时直接 `replace` 到 `/standard-report/:slug`
  - 没有 slug 时回首页

### 2. 首页标准卡直接进标准报告页

- 文件：[InputPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/InputPage.tsx)
- 处理：
  - 首页 6 张标准卡点击后不再进导览页
  - 直接进入对应的标准报告页
  - 用户可见文案从 `先看标准导览` 改成 `先看标准报告`

### 3. 返回首页的轻提示合同改名

- 文件：
  - [standard-report.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/standard-report.ts)
  - [StandardReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/StandardReportPage.tsx)
  - [InputPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/InputPage.tsx)
- 处理：
  - `buildStandardPrefillState` 改成 `buildStandardReportPrefillState`
  - 页面 state 里的 `prefillSource` 从 `standard-case` 改成 `standard-report`
  - 避免代码层继续沿用旧概念

### 4. 清理无效路由常量和测试

- 文件：
  - [routes.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/router/routes.ts)
  - [StandardCasePage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/StandardCasePage.test.tsx)
  - [StandardReportPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/StandardReportPage.test.tsx)
  - [InputPage.test.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/__tests__/InputPage.test.tsx)
- 处理：
  - 删除已无调用的 `ROUTES.STANDARD_CASE`
  - 保留旧路由，但只测“兼容跳转”
  - 更新标准报告页和输入页测试，锁住新的 `standard-report` 合同

## 验证

- `cd frontend && npm test -- src/pages/__tests__/StandardCasePage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/InputPage.test.tsx`
  - `11 passed`
- `cd frontend && npm run build`
  - 通过
- Playwright 真实浏览器确认：
  - 打开 `http://127.0.0.1:3006/standard-case/home-cleaning`
  - 页面直接落到 `http://127.0.0.1:3006/standard-report/home-cleaning`
  - 回首页后，6 张标准卡按钮文案已变成 `先看标准报告`

## 下一步系统性的计划是什么？

1. 继续按用户节奏打磨标准报告页细节，直到这套结构完全稳定。
2. 然后把同样的章节顺序和平铺逻辑同步到真实报告页 `ReportPage.tsx`。
3. 标准报告页和真实报告页统一后，再处理内容层的小问题，例如个别卡片的句子过碎、机会卡字段过硬。

## 这次执行的价值是什么？

- 这次不是“再做一个新页面”，而是把一层已经没价值的页面彻底拿掉。
- 现在标准样板链路更短了：
  - 首页看到题
  - 直接看标准报告
  - 看完回首页写自己的问题
- 这让首页标准卡终于从“导览入口”变成了真正的“标准报告入口”。
