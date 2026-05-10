# phase810

- 时间：2026-04-14
- 主题：详情页展示层优化

## 改动文件

- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.scss`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.scss`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.tsx`

## 结果

- 详情页正文、来源判断、长列表整体字号和行高上调，长中文段落更易读。
- 详情引用区补齐独立样式：
  - `detail-quote-text`
  - `detail-quote-meta`
  - `detail-quote-action-row`
- `展开全文` 从正文里拆出来，改成独立动作行，不再挂在句子中间。
- 裸链接引用会在展示层清掉 URL，避免原帖预览链接直接占满卡片。
- 构建通过：
  - `npm run build:weapp`
