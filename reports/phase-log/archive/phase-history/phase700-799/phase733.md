# Phase 733

## 本轮目标

把刚稳定住的 `hot` 候选真正推进到前台，验证 `hot-ops` 已经能完成 `seed -> review -> publish -> snapshot` 闭环。

## 实现

- 对 3 条 runtime `hot` 候选完成人工收稿并发布：
  - `draft-cand-ai-automation-1sftdkl-validate`
  - `draft-cand-ai-automation-1sg0kpp-validate`
  - `draft-cand-business-growth-ops-1sepe9p-validate`
- 收稿重点：
  - 去掉旧模板句
  - 去掉“正确的废话”
  - 统一改成热点口径：`这帖为什么火 / 大家在吵什么`
- 推送最新 mini snapshot：
  - `release-abc1ca2b006e`

## 验证

- `python backend/scripts/hotpost/review_cards.py publish <draft_id>`
- `python backend/scripts/hotpost/push_mini_snapshot.py`
- 当前发布状态：
  - `published_total: 90`
  - `published_hot_total: 6`

## 本轮新增热点卡

- `OpenAI 这帖火起来，不是因为谁营收更高，而是两家的算法根本没法直接放一张表里比。`
- `前 OpenAI 高管一句“像在召唤外星人”，把讨论点从模型强不强拽到了失控感上。`
- `GEO 一冒头，DigitalMarketing 里吵的已经不是新术语，而是 SEO 那套到底还够不够用。`

## 结论

- `hot` 这条线现在已经不是只有 runtime 候选，已经重新形成前台可见闭环。
- 阶段性结果是：
  - 规则干净了
  - 审计口径对齐了
  - 前台热点数从 `3 -> 6`
- 下一步就不再是“能不能发出来”，而是继续把 `hot` 供给密度和运营吞吐往上抬。

## 下一步

1. 继续按 `hot-ops` 跑，争取把 `published_hot_total` 往 `8+` 拉。
2. 继续补 AI / 增长 / 电商里的争论型供给。
3. 继续提高单轮出卡量，但不回到弱证据和模板稿。
