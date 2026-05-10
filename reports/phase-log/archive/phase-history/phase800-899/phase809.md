# phase809

- 时间：2026-04-14
- 主题：首页轻卡视觉收口

## 改动文件

- `hotpost-mini/hotpost-mini-app/src/components/CluePreviewCard.tsx`
- `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`

## 结果

- 首页轻卡结构不变，只补视觉层：
  - 卡面增加更轻的层次、描边和顶部 lane 色带
  - `signal / breakdown` 核心块改成更像摘要条的编辑式信息块
  - `hot` 的争议图改成更稳的横向比例条外观
  - CTA 收成页脚分割线，不再悬空
- 结构审计保持通过：
  - `decision = publish`
  - `scanability_pass = true`
  - `cta_clarity_pass = true`
  - `detail_weight_removed_pass = true`
  - `lane_core_block_pass = true`
  - `lane_structure_consistency_pass = true`
- 构建通过：
  - `npm run build:weapp`
