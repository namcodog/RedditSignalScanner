# Organic + Category Pack Closure

日期：2026-04-08

## 结论

- `organic-discovery` 已跑出 keep：
  - baseline `human_summary_tight_why_now_v1 = 0/2 pass`
  - `organic_discovery_readout_v1 = 2/2 pass`
- `category-winds` 已跑出 keep：
  - baseline `human_summary_tight_why_now_v1 = 0/2 pass`
  - `category_winds_readout_v1 = 2/2 pass`

## 这轮真正完成了什么

1. `organic-discovery`
- 补了 pack 专用覆盖层：
  - `backend/app/services/hotpost/organic_discovery_overrides.py`
- 接入生产生成链：
  - `backend/app/services/hotpost/card_content_generator.py`
- canary 已验证为 keep

2. `category-winds`
- 先修供给，不直接硬做 prompt：
  - pack 改成 `search-first`
  - `problem -> change -> category`
  - 单 spec 只取 `1` 条
  - 卖家社区 promo/sticky 不再吃掉真实帖子
  - `reddit_candidate_mapper` 新增 bot / scam warning comment 过滤
- 再补 pack 专用覆盖层：
  - `backend/app/services/hotpost/category_winds_overrides.py`
- live canary 已验证为 keep

## 当前稳定资产

- 全局 signal 基线：`human_summary_tight_why_now_v1`
- pack 专用写法：
  - `paid_econ_signal_readout_v2`
  - `selection_signal_readout_v1`
  - `agent_builder_signal_readout_v1`
  - `organic_discovery_readout_v1`
  - `category_winds_readout_v1`
- `signal input quality gate`
- `signal judge`
- `breakdown auto materialize`

## 边界

- 这轮完成的是 `signal pack` 扩展，不是 `breakdown skill` 优化。
- `tools-efficiency` 仍保持冻结，不因为这轮成功就恢复实验。
