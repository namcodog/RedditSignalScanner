# Phase 804

## 时间

- 2026-04-14 00:20 CST

## 本轮目标

- 不再改 prompt / planner / schema / named topic
- 先按 `L0 intake freshness` 过时间层
- 再按审计结论补齐 `15-baseline` 的结果层
- 真正发出一轮满足 `9/4/2`、`5/5/5` 的 15 张

## 发现

- 默认 `offline_publish_plan-15` 在时间层已过，但结果层没有过：
  - lane 会漂到 `4 / 6 / 5`
  - scope 会漂到 `5 / 6 / 4`
- 审计后确认不是规则链问题，而是发布面缺一个可直接使用的 `business-growth-ops` 热点位和若干 signal draft 的唯一缺口。
- 现有 8 个 signal draft 都只缺 `detail.min_test_action`，补完即可直接变成 ready。
- 新增 `draft-cand-business-growth-ops-1sk5wuq-validate` 后，可改用：
  - hot：`AI 2 / BGO 2`
  - signal：`AI 3 / BGO 3 / Ecom 3`
  - breakdown：`Ecom 2`
  从而同时满足：
  - lane：`signal 9 / hot 4 / breakdown 2`
  - scope：`5 / 5 / 5`
  - named topic：`PASS`
  - freshness：`publish`

## 实际执行

- 补齐以下 draft 的 `min_test_action`：
  - `draft-cand-ai-automation-1sigrts-validate`
  - `draft-cand-ai-automation-1siosn2-validate`
  - `draft-cand-ai-automation-1sjd3tj-validate`
  - `draft-cand-business-growth-ops-1sjz5b7-validate`
  - `draft-cand-business-growth-ops-1skbj17-validate`
  - `draft-cand-ecommerce-sellers-1sjpize-validate`
  - `draft-cand-ecommerce-sellers-1sk0uqc-validate`
  - `draft-cand-ecommerce-sellers-1sk886m-validate`
- live seed 新增强 BGO hot draft：
  - `draft-cand-business-growth-ops-1sk5wuq-validate`
- 生成并验证全 draft 版人工发布面：
  - `backend/tmp/manual-publish-plan-15-drafts-only.json`
  - `backend/tmp/manual-publish-plan-15-drafts-only-eval.json`
- 实判结果：
  - lane：`4 / 9 / 2`
  - scope：`5 / 5 / 5`
  - freshness：`publish`
- 按这 15 张直接发布，并重建 mini snapshot

## 发布结果

- 新 release：`release-7afdf4f2f277`
- `card_count = 185`
- `feed_contract = 30 / 30`
- `cloud_db copy guard = ok`

## 当前结论

- `15-baseline` 这轮已经真正跑通，不再是纸面合同
- 今天的正确执行方式是：
  - 先过 freshness gate
  - 如果默认 plan 结果层不过，就做一次人工审计替换
  - 替换只改发布面，不回头改规则链
- `18` 仍然只是 `near-publish boundary`，不恢复为当前 delivery target

## 关键产物

- `backend/tmp/manual-publish-plan-15-drafts-only.json`
- `backend/tmp/manual-publish-plan-15-drafts-only-eval.json`
- `backend/data/hotpost/mini_snapshots/cloud_db/mini_release_meta.wechat-import.json`
- `backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.wechat-import.json`
