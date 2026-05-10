## 时间
- 2026-03-29

## 发现了什么
1. 首页确实还有三个体验口子：
   - 三张模式卡片描述没有对齐当前价值口径。
   - 指定社区默认就带 `r/startups`，会误导用户以为是必选。
   - 输入框提示是固定模板，用户切模式后没有对应引导。
2. 指定社区后端能力是存在的：
   - `HotpostSearchRequest` 已支持 `subreddits` 字段。
   - 但小程序之前没有把社区参数透传到后端。

## 是否需要修复
- 需要。
- 这轮只改首页交互，不扩到详情页。

## 精确修复方法
### 1. 三张卡片价值文案对齐当前口径
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx`
- 改动：
  - `热点追踪`：现在什么值得追，为什么是现在
  - `痛点挖掘`：用户到底在痛什么
  - `机会发现`：这个具体问题值不值得做

### 2. 输入模板改成随模式动态变化
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/index/index.scss`
- 改动：
  - placeholder 随模式切换
  - 输入框下方增加一条更具体的输入建议（`input-hint`）

### 3. 指定社区默认空 + 真正透传后端
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/loading/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`
- 改动：
  - 默认不预置社区标签
  - 首页带上 `subs` 参数跳转 loading
  - loading 解析 `subs` 并传给 `createHotpostSearch`
  - `createHotpostSearch` 正式支持 `subreddits`

## 验证
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`

## 这次执行的价值
- 首页从“能用”推进到“更顺手”：
  - 模式价值更清楚
  - 输入引导更贴模式
  - 指定社区不再是假入口，已走到后端真实能力
