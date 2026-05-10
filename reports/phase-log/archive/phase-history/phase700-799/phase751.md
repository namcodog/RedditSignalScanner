# Phase 751 - 小程序详情页 P2 可维护性优化

## 发现

- `detail-sections.tsx` 的 `ValidateBlock` 把 signal/hot 两套详情标题全部写在一条 JSX 长行里。
- 页面能跑，但后续继续精修文案时容易在长行里误改字段、误伤产品态。

## 修复

- 将 signal/hot 两套详情标题拆成 `SIGNAL_VALIDATE_LABELS` 和 `HOT_VALIDATE_LABELS`。
- `ValidateBlock` 只负责选择 labels 并渲染字段，不再直接嵌套大量三元表达式。
- 不改数据结构、不改样式、不改云同步链路。

## 验证

- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp` -> passed。

## 结论

- P2 已收口为纯可维护性优化。
- 后续如果继续调详情页标题，只需要改 labels 配置，避免在 JSX 长行里误伤页面结构。
