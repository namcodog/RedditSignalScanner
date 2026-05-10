# phase710

## 日期
2026-04-09

## 本轮结果
- 继续按 `signal-ops / breakdown-ops` 跑稳态运营。
- 修正 `signal_input_quality.py` 中 `meta_community_complaint` 误杀，避免把真正的 SEO / listing 讨论挡掉。
- 新增两条反误杀测试并通过。
- 新发布 2 张 `信号快报`：
  - `card-cand-business-growth-ops-1sffkzh-validate`
  - `card-cand-ecommerce-sellers-1sf21km-validate`
- 删除不合格 draft：
  - `draft-cand-ai-automation-1sf4rk9-validate`
  - `draft-cand-ai-automation-1sc7byy-validate`
- 推送最新 mini snapshot：
  - `release-0a9a14a1954c`
  - `card_count = 62`

## 验证
- `pytest backend/tests/services/hotpost/test_signal_input_quality.py -q`
- `python backend/scripts/hotpost/review_cards.py seed ...`
- `python backend/scripts/hotpost/review_cards.py publish ...`
- `python backend/scripts/hotpost/push_mini_snapshot.py`

## 当前状态
- published: `62`
- by_domain:
  - `ai-automation = 25`
  - `business-growth-ops = 22`
  - `ecommerce-sellers = 15`
- by_lane:
  - `signal = 37`
  - `breakdown = 24`
  - `hot = 1`
- drafts: `0`

## 结论
- 这轮补卡的真实瓶颈不是 review，而是新鲜候选质量偏弱。
- `爆贴热点` 还没有足够稳定的新料，不应为了补量硬发。
- 当前应继续稳态 collect，并优先寻找 listing-first 的真实热点增量。
