# phase834

## 本轮目标
- 首页卡片补充“来自哪个社区”的来源信息，不改数据结构，不把首页重新做重。

## 实际改动
- `hotpost-mini/hotpost-mini-app/src/components/CluePreviewCard.tsx`
  - 新增首页社区来源行
  - 优先显示 `top_community`
  - 缺失时回退到 `source_scope_name`
- `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`
  - 新增社区来源行样式
  - 采用轻量 kicker + pill，不和标题、CTA 抢视觉重心

## 设计口径
- 位置：卡片主体和 `看详情` 之间
- 文案：`来自社区`
- 值：例如 `r/OpenAI`
- 目标：补来源感，不增加首页阅读负担

## 验证
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
  - 通过

## 下一步
- 开发者工具重新编译后，只验证一件事：
  - 首页三条 lane 的卡片上是否都能看到社区来源行
