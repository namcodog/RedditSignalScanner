# Phase 823 - 首页长标题显示优化

## 发现
- 首页轻卡进一步收轻后，`hot` 与 `breakdown` 的部分标题依然在两行内截断过早。
- 这不是样式 bug，而是首页轻卡高度约束与长标题文案本身发生冲突。
- 仅靠前端无法保证“所有标题都在两行内完整显示”；前端只能在标题行数和字号之间做折中。

## 调整
- 在 `clues.scss` 中仅对首页的 `hot` / `breakdown` 卡标题做差异化处理：
  - 放宽为 3 行显示
  - 字号从 `37rpx` 收到 `35rpx`
  - 行高同步微调
- `signal` 继续保持 2 行，避免首页整体重新变成长卡墙。

## 文件
- `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`

## 验证
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：通过

## 结论
- 这轮是首页轻卡约束下更合理的前端折中。
- 如果后面仍然有个别标题过长，下一步应该改标题生成策略，而不是继续无限放大卡片高度。
