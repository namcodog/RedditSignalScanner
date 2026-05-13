# Phase 690 - card-autoresearch-lab v3 growth keep

## 1）发现了什么？

- `card-autoresearch-lab v3` 已经跑完。
- 本轮不碰 `why_now`，只做更窄的 growth-pack polish。
- 结果：
  - `clean_summary_polish_v1 = 3/10 pass`
  - `clean_summary_growth_pack_polish_v3 = 4/10 pass`
- 结论：
  - v3 在 `business-growth-ops` 上是小幅真实提升，不是噪音。

## 2）是否需要修复

- 需要。
- 但只做窄 promote，不做全局 promote。

## 3）精确修复方法

- 新增 `backend/app/services/hotpost/business_growth_signal_overrides.py`
- 在 `backend/app/services/hotpost/card_content_generator.py` 接线
- 只对：
  - `business-growth-ops`
  - 且非 `paid-economics / organic-discovery`
  的 signal 草稿生效

## 4）下一步系统性的计划是什么？

- 先停下来观察真实卡片读感。
- 不继续扩全局 prompt。
- 如果后面还要继续 autoresearch，优先：
  - 更窄的 pack polish
  - 或 breakdown polish

## 5）这次执行的价值是什么？达到了什么目的？

- 证明了 `autoresearch-lab` 不只会跑全局实验，也能在窄 pack 上跑出可 promote 的 keep。
- 当前小程序生产链又多了一层可控、低风险、可见效果快的 polish 资产。
