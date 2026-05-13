# Phase 440 - 标准样板前端交互重构

## 发现了什么

- 首页 6 张标准卡之前直接跳静态报告页，用户还没建立阅读预期就被塞进结果页，节奏错了。
- 标准报告页把其他标准题按钮混进完整报告视图，造成“一题看报告时还夹着别的题”的干扰。
- 用户能看到 `topic_profile`、`task_id` 这类内部字段，属于系统实现细节，不该暴露。
- 完整报告页对 HTML / Markdown 没有做分流，遇到 markdown 文本时会直接出现“# / ## / 换行飞掉”的阅读灾难。

## 是否需要修复

- 需要，这是标准展示轨的 P0 体验问题。
- 如果这条链不顺，用户会误以为我们只有一页静态卡片，而不是一个完整的“先导览、再阅读、再改写”的产品路径。

## 精确修复方法

### 1. 标准卡入口改成“先导览，再进报告”

- 新增 `StandardCasePage`
- 路由：`/standard-case/:slug`
- 首页 6 张标准卡现在先进入标准导览页，再选择看卡片版或完整报告

### 2. 标准报告页重做信息层级

- 去掉内部字段：
  - `topic_profile_id`
  - `task_id`
- 去掉完整报告页里的“其他标准题列表”
- 顶部改成：
  - 标准报告身份
  - 校验时间
  - 核心指标
  - 结论摘要

### 3. 完整报告阅读修复

- 新增标准快照加载工具 `standard-report.ts`
- `StandardReportPage` 现在会分流：
  - `report_html` 是 HTML 时，用文档视图渲染
  - 只有 markdown 时，用 `pre-wrap + break-words` 安全渲染
- 解决长文本飞出和 markdown 原样挤成一团的问题

### 4. 首页文案与交互修正

- 标准卡不再宣称“点开直接看标准结果”
- 改成“先看标准导览，再决定是否带回输入框”
- 标准卡从可点击 `div` 改为语义化 `button`

## 验证

- `cd frontend && npm test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/StandardCasePage.test.tsx`
  - `9 passed`
- `cd frontend && npm run build`
  - 通过

## 这次执行的价值

- 把标准展示轨重新拉回产品逻辑：
  - 先理解这题是什么
  - 再看它为什么值得看
  - 最后再读完整报告
- 这条链现在比之前更接近 `primelogic.cc` 那种“先给阅读入口，再展开内容层次”的节奏。
- 当前剩余重点已经不是“报告页会不会乱”，而是和你继续把整体交互地图聊透，统一到真正的主链产品体验上。

## 追加收口 - 视觉层级强化

- 继续参考 `primelogic.cc` 的视觉语言做了一轮强化，不是照抄，而是吸收这几个核心点：
  - 暖白底 + 金棕点缀
  - 大标题留白更足
  - 主判断卡更重更深
  - 次级说明卡更轻更浅
  - 文档阅读区更窄，避免一整屏文字平铺
- 已新增一组 `editorial-*` 视觉类：
  - `editorial-frame`
  - `editorial-section`
  - `editorial-card-primary`
  - `editorial-card-secondary`
  - `editorial-metric`
  - `editorial-tab`
- 标准导览页和标准报告页都已切到这套更强层级的样式。
- 验证：
  - 前端定向测试仍然 `9 passed`
  - `frontend build` 仍然通过
