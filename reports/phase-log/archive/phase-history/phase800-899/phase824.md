# Phase 824

## 本轮目标
- 在不改数据和页面结构的前提下，继续推进小程序首页与详情页的视觉质感。

## 实际改动
- 首页：
  - 强化 sticky header 的毛玻璃层次和顶部卡片的编辑感。
  - 调整 tab 的底色、圆角和激活态，使其更像内容筛选器，不像默认按钮。
  - 提升卡片 surface 质感，加入更轻的径向高光和更稳的内阴影。
  - 收紧 `signal / breakdown / hot` 核心块背景，让信息块更像正文引导区。
  - 优化 `hot` 争议图的轨道、填充和 CTA pill，让数据区更像产品卡面，而不是功能稿。
- 详情页：
  - 给 `READ / PROOF / TRUST` 三段增加更清楚的节奏感和分段间距。
  - Hero、争议雷达、信任底座都补了更明确的 tonal layering。
  - 引用区首条证据做了轻微抬升，后续引用弱化，提升阅读导向。
  - 分析区 warm item 和 inline pill 的材质感加强。

## 涉及文件
- `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-immersive.scss`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.scss`

## 验证
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp` 通过

## 结论
- 本轮继续沿用 Alexandria 的高端编辑感方向。
- 只改渲染层和样式层，没有碰接口、数据和业务逻辑。
