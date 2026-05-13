---
name: breakdown-ops
description: 日常 breakdown 产卡操作；用于 suggestion、materialize draft、人工 review、overlap 预警和发布检查。
---

# Breakdown Ops

## 何时使用

- 跑日常 breakdown 产卡
- materialize write draft
- 人工 review breakdown 草稿
- 跑 overlap 预警
- 发布 breakdown 卡

## 不做什么

- 不重写 suggestion 聚类逻辑
- 不复制 coherence gate / judge 规则
- 不替代 breakdown skill optimization

## 使用顺序

1. 先读：
   - `docs/sop/2026-04-09-稳态运营成功SOP.md`
   - `docs/sop/2026-04-08-评审与发布SOP.md`
2. 再按这个顺序执行：
   - `make hotpost-publish-until-exhausted`
   - `make hotpost-breakdown-materialize`
   - `python backend/scripts/hotpost/review_cards.py queue --type write --limit 20`
   - `make hotpost-breakdown-overlap`
   - `python backend/scripts/hotpost/review_cards.py show-draft <draft_id>`
   - `python backend/scripts/hotpost/review_cards.py publish <draft_id>`
   - `python backend/scripts/hotpost/push_mini_snapshot.py`
   - 再回到 `make hotpost-publish-until-exhausted`

## 判断边界

- 自动只到 write draft
- 发布继续人工
- overlap audit 只是预警，不是最终裁决
- 具体卡片质量判断，以当前 backend 代码和正式 judge/gate 为准，不以本 skill 为准
- 日常默认先跑 `all-scope` 基础轮，再判断要不要把某个题材做厚
- 时间窗口默认先看 `7d`；只有确认 `7d` 已吃干净后，才开 `15d` 做扩容
- 如果同题已经有 `signal / hot` 在当天主发池里，`breakdown` 默认先当替代厚稿，不默认同天并发
- `1.0` 阶段允许比后期产品更短、更轻，但不能退成“长一点的 signal”
- publish 后必须核对 mini snapshot 的 release 已更新
- 这轮只有在没有新的净新增价值时才停，不是发一两张就收
