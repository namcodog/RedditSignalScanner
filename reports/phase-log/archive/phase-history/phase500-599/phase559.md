# Phase 559 - Mini Hotpost 痛点挖掘详情页真链路接线

## 发现了什么？
- `loading` 其实早就给 `rant` 留了真入口，真正缺的是：
  1. 首页不放行 `rant`
  2. `friction` 页面还是整页 mock
  3. 小程序详情快照没有保存 `pain_points / competitor_mentions / migration_intent / notes`
- 也就是说，这条线不是从零开始，而是少了最后一段接线。

## 是否需要修复？
- 需要。
- 这轮目标不是把 `rant` 打磨到终态，而是先把“真链路 + 真结构”接起来。

## 精确修复方法
- 更新 [hotpost.ts](../../hotpost-mini/hotpost-mini-app/src/services/hotpost.ts)
  - 补 `HotpostPainPoint / HotpostCompetitorMention / HotpostMigrationIntent`
  - `HotpostResult` 新增：
    - `pain_points`
    - `competitor_mentions`
    - `migration_intent`
    - `notes`
- 更新 [hotpost-detail-cache.ts](../../hotpost-mini/hotpost-mini-app/src/services/hotpost-detail-cache.ts)
  - 详情快照补存 `pain_points / competitor_mentions / migration_intent / notes`
- 更新 [index.tsx](../../hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx)
  - 首页放行 `rant`
  - 仅继续拦截 `opportunity`
- 更新 [history/index.tsx](../../hotpost-mini/hotpost-mini-app/src/pages/history/index.tsx)
  - `rant` 记录页现在可以直接进入真实详情页
- 新增 `friction` 真页面：
  - [friction/index.tsx](../../hotpost-mini/hotpost-mini-app/src/pages/friction/index.tsx)
  - [friction/helpers.ts](../../hotpost-mini/hotpost-mini-app/src/pages/friction/helpers.ts)
  - [friction/sections.tsx](../../hotpost-mini/hotpost-mini-app/src/pages/friction/sections.tsx)
  - [friction/index.scss](../../hotpost-mini/hotpost-mini-app/src/pages/friction/index.scss)
- 页面严格按后端字段走，不再套 `trending`：
  - `summary`
  - `pain_points`
  - `competitor_mentions`
  - `migration_intent`
  - `top_posts`
  - `top_quotes`
  - `next_steps`

## 当前页面结构
1. 分析摘要
2. 核心痛点
3. 流失与替代
4. 代表帖子
5. 用户原话
6. 下一步

## 验证
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
- 结果：`Compiled successfully`

## 下一步
- 跑 1 条真实 `rant` query
- 看这几个字段是不是都能真实落到页面：
  - `pain_points`
  - `migration_intent`
  - `competitor_mentions`
  - `top_quotes`
- 然后再收一轮：
  - 解读厚度
  - 文案大白话
  - 卡片信息密度
