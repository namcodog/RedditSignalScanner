# Phase 441 - 标准样板接回真实分析主链

## 发现了什么

- `phase440` 已经把标准展示轨做顺了，但它和真实输入主链之间还是弱连接。
- 用户从标准导览页或标准报告页回到输入框时，之前只会带回一段 prompt：
  - 首页知道“有内容回来了”
  - 但不知道这其实来自哪份标准样板
  - 也不会沿用对应的 `topic_profile_id`
- 结果就是：
  - 这条链更像“复制一段文字”
  - 不像“先看标准样板，再切进真实分析”

## 是否需要修复

- 需要，这是当前标准展示轨和主链之间最后一段产品断层。
- 如果不补，标准样板仍然更像展示页，而不是主链的自然起点。

## 精确修复方法

### 1. 标准样板带回状态升级

- `frontend/src/lib/standard-report.ts`
- `buildStandardPrefillState()` 现在不只带 prompt，还会一起带：
  - `prefillSource=standard-case`
  - `prefillTopicProfileId`
  - `prefillStandardTitle`

### 2. 输入页正式识别“标准样板带回”

- `frontend/src/pages/InputPage.tsx`
- 新增 `standard-case` 来源口径：
  - banner 改成 `已带回这份标准样板`
  - 会显示 `当前起点：<标准题标题>`
- 如果用户直接拿原题开跑：
  - 会沿用对应 `topic_profile_id`
  - 继续走黄金路径
- 如果用户改了描述：
  - `selectedPromptSnapshot` 会自动失效
  - `topic_profile_id` 自动解绑
  - 避免把改过的题还当成固定标准题去跑

### 3. 标准报告页补最后一颗 CTA

- `frontend/src/pages/StandardReportPage.tsx`
- 新增底部动作区：
  - `用这题跑真实分析`
- 不管用户在看卡片版还是完整报告，都能直接切回输入主链

### 4. 标准导览页同步走新合同

- `frontend/src/pages/StandardCasePage.tsx`
- `用这题做起点` 现在也会带完整的标准样板来源状态回首页

## 验证

- `cd frontend && npm test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/StandardCasePage.test.tsx`
  - `11 passed`
- `cd frontend && npm run build`
  - 通过

## 这次执行的价值

- 标准样板不再只是“给你看一眼”，而是真正能顺手接到真实分析主链。
- 现在这条链已经更完整：
  - 先看标准导览
  - 再看标准报告
  - 最后把这题带回输入框，直接改成自己的方向

## 下一步系统性计划

- 继续收主链体验地图，不再把“标准展示轨”和“真实分析轨”当两套页面。
- 下一轮重点应该放在：
  - 输入页如何更明确区分“标准起点”和“自由输入”
  - progress / report / standard 三条返回链是否还能继续统一
  - 真实浏览器里从标准样板起跑的整条链是否顺滑
