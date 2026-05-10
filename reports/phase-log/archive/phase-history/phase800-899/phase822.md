# Phase 822 - 首页轻卡细节收口

## 范围
- 只动首页卡片层与首页 tab 切换交互。
- 不动详情页数据、不动接口、不动发布链。

## 本次收口
- 首页隐藏收藏按钮，避免首页与详情页重复动作入口。
- 首页 tab 切换统一执行 `pageScrollTo(0)`，切换 `全部 / 潜力快帖 / 跨区热议 / 近期爆帖` 时默认回到顶部。
- 首页卡片标题缩一档：
  - `40rpx -> 37rpx`
  - 保持两行截断，但让更多卡片标题能在两行内读完。
- `hot` 首页卡把原先无标签的说明块改成：
  - 标题：`分歧点`
  - 内容优先显示 `controversy_chart.debate_focus`
  - 若无图表再回退 `summary_line`

## 文件
- `hotpost-mini/hotpost-mini-app/src/components/CluePreviewCard.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`

## 验证
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：通过

## 结果
- 首页卡片进一步摆脱“详情缩略版”感觉。
- `hot` 卡从“长说明”变成更短、更清楚的“分歧点”入口。
- 首页交互更符合轻卡入口页逻辑。
