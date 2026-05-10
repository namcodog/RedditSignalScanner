# phase808

- 时间：2026-04-14
- 主题：首页 light-card 回灌

## 改动文件

- `hotpost-mini/hotpost-mini-app/src/components/CluePreviewCard.tsx`
- `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`

## 结果

- 首页按 `lane` 显式拆模板：
  - `signal`：标题 + 判断变化 + 谁最该关注 + 看详情
  - `breakdown`：标题 + 核心洞察 + 看详情
  - `hot`：标题 + 争议图 + 一句 caption + 看详情
- 已从首页移除：
  - `why_now`
  - `preview_quote / quote block`
  - `HotControversyStanceRows`
  - 非 hot 的说明盒子堆叠
- evaluator 结果：
  - `decision = publish`
  - `scanability_pass = true`
  - `cta_clarity_pass = true`
  - `detail_weight_removed_pass = true`
  - `lane_core_block_pass = true`
  - `lane_structure_consistency_pass = true`
