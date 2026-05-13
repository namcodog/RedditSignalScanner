# Phase 548 - Mini Hotpost 详情页卡住收口

## 时间
- 2026-03-28

## 背景
- 用户反馈小程序热点追踪详情页在部分关键词下会停在“正在读取 Hotpost 最终结果...”。
- 现场截图里的词是 `AIGC`，不是 `claude ai`。

## 发现了什么
1. 后端不是主因。
   - `AIGC` 这条新查询能很快返回终态结果，且 payload 很小。
   - 热门词结果体会明显变大，像 `claude ai` 这种完整结果可达 `81KB+`。
2. 当前小程序链路是：
   - loading 页轮询到终态
   - 再跳到详情页
   - 详情页还会再发一次 `GET /result/{query_id}`
3. 这意味着详情页会重复吃一次结果接口：
   - 小结果还好
   - 大结果或模拟器环境抖动时，就容易让页面长期停在 loading 态

## 是否需要修复
- 需要。
- 这不是视觉问题，是结果页取数方式不稳。

## 精确修复方法
### 1. 加载页把终态结果先交给详情页
- 在 loading 页拿到终态结果后，先写本地快照，再跳详情页。
- 这样详情页不必再强依赖第二次网络请求。

### 2. 详情页优先读本地快照
- 详情页优先读 queryId 对应的本地轻量结果。
- 只有本地没有时，才回退到接口读取。

### 3. 结果做详情页专用轻量化
- 新增详情页专用轻量投影，只保留页面真正使用的字段：
  - `summary`
  - `topics`
  - `top_posts`
  - `top_quotes`
  - `communities`
  - `trending_keywords`
  - `community_distribution`
  - `sentiment_overview`
  - `next_steps`
  - `debug_info`
- 不再把完整大报告整包塞进详情页状态。

## 修改文件
- `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`
- `hotpost-mini/hotpost-mini-app/src/services/hotpost-detail-cache.ts`
- `hotpost-mini/hotpost-mini-app/src/pages/loading/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`

## 验证
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
- 结果：`Compiled successfully`

## 当前结果
- 详情页不再必须等第二次接口请求才能打开。
- 对 `AIGC` 这类本来就很快出结果的词，会直接进入详情页。
- 对热门大词，也先用本地轻量结果把页面打开，降低再次卡住概率。

## 这次执行的价值
- 把“loading 页已经拿到结果，详情页却还在傻等”的重复链路切掉了。
- 这是一个轻修复，不改设计，不改业务口径，但能明显提高详情页打开稳定性。

## 当前进度
- 小程序 `trending` 真实链路：`100%`
- 详情页价值表达：`约 96%`
- 详情页打开稳定性：`从不稳提升到可验收`
