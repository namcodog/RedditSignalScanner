# Phase 1141 - Hotpost R12 与品牌候选收尾

## 这轮达到的目的

- 完成 2026-05-18 发布后的社区入池预审和品牌候选复核。
- 修掉 R12 预审把同一社区拆成两条待写入记录的风险。

## 当前状态变化

- `r/eBaySellerAdvice` 两条 promote 证据已合并成一条 R12 项，并已写入 Dev community pool；复跑 dry-run 显示 `skipped_existing=1 / would_insert=0`，确认不会重复写。
- `Mirror` 已判定为小写动词误识别，不再作为新品牌候选或语义库候选。
- 品牌质量审查新增大小写敏感歧义词规则，`mirror` 这类普通动词不会再被当品牌自动验证。

## 还没完成什么

- `r/eBaySellerAdvice` 已进入 Dev community pool，但还没反推到 Gold / 小程序展示层。
- 今日 final no-collect gate 仍有 `actual_total=8`，系统收口不是完全清空。

## 下一步做什么

- 后续观察 `r/eBaySellerAdvice` 在日常运营里是否继续稳定产出可发布卡，再决定是否进入更高层级治理。
- 后续品牌 sidecar 继续只做上下文增强，不进入发布门槛和首页排序。
