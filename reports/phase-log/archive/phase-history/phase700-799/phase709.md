# phase709

## 发现了什么

- 按现有 `signal-ops / breakdown-ops` 真跑一轮后，当前主链已经进入可重复的稳态运营。
- 这轮不是盲发：
  - `published 57 -> 60`
  - 新发 `3` 张卡
  - 其中包括第一张真正按 `lane=hot` 发出的 `爆贴热点`
- 这轮也暴露了一个真实运营边界：
  - 候选池里混着旧卡残留
  - seed 时如果报 `Published card already exists`，说明去重正常，不是坏了

## 本轮发布

- `card-cand-ai-automation-1sfqix8-validate`
- `card-cand-ai-automation-1saabgz-validate`
- `card-cand-ecommerce-sellers-1sbqw0m-validate`

## 本轮清理

- 清掉不该发的坏 draft：
  - `draft-cand-ai-automation-1sc7byy-validate`
  - `draft-cand-ai-automation-1sf4rk9-validate`

## 当前状态

- `release_id = release-4f134e0f7e69`
- `card_count = 60`
- `draft_count = 0`
- `candidate_count = 24`
- `breakdown materialize = 0`
- `breakdown overlap = 0`

## 结果

- mini snapshot 已重新推送，开发工具可直接看到新卡
- 已把这轮真实跑通的动作收成：
  - [2026-04-09-稳态运营成功SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-04-09-%E7%A8%B3%E6%80%81%E8%BF%90%E8%90%A5%E6%88%90%E5%8A%9FSOP.md)

## 结论

- 现在这套 hotpost 工作流已经不只是“能跑”，而是有了一份经真实运营验证过的成功 SOP。
