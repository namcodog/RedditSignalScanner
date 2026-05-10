# phase718 - signal 稳态 SOP 收口 + 候选拒绝记忆

## 本轮完成

- 给 `signal-ops` 补了一个很小的“人工拒绝候选”能力：
  - `python backend/scripts/hotpost/review_cards.py reject <candidate_id> --reason <reason>`
- validate 队列现在会先自动跳过：
  - 已发布重复卡
  - 已在 draft 队列里的卡
  - 被 `signal input quality gate` 明确拦住的弱证据卡
  - 已被人工拒绝过的坏候选
- 更新稳态运营成功 SOP，把这条边界写死：
  - 当 validate 队列只剩“被 gate 拦住”或“正确的废话”时，直接停，不为补量硬发
- 清掉了两张会反复污染运营节奏的坏候选：
  - `cand-ai-automation-1sc7byy`
  - `cand-business-growth-ops-1sg88t5`
- 清掉了一个明显强拼的 breakdown 草稿：
  - `draft-group-ecommerce-sellers-10b4d54273`

## 当前阶段结果

- `published = 72`
- `lane` 分布：
  - `signal = 45`
  - `hot = 3`
  - `breakdown = 24`
- `scope` 分布：
  - `ai-automation = 28`
  - `business-growth-ops = 26`
  - `ecommerce-sellers = 18`
- 当前 `validate` 队列：空
- 当前 `write` 草稿：空

## 验证

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_review_queue_policy.py backend/tests/services/hotpost/test_card_selection_policy.py backend/tests/services/hotpost/test_card_lane_policy.py -q`
  - 结果：`10 passed`
- `python -m py_compile backend/scripts/hotpost/review_cards.py backend/app/services/hotpost/review_queue_policy.py backend/app/services/hotpost/card_review_rejection_store.py backend/app/services/hotpost/card_draft_store.py`
  - 结果：通过
- `python backend/scripts/hotpost/review_cards.py queue --type validate --limit 20`
  - 在 reject 两张坏候选后，队列收到了“只剩空/该停”的状态
- `python backend/scripts/hotpost/review_cards.py publish draft-cand-ai-automation-1sg9hyb-validate`
  - 结果：补出 1 张新 AI 快报
- `python backend/scripts/hotpost/push_mini_snapshot.py`
  - 结果：`release-92e5a8d219fd`，`card_count = 72`

## 这轮真正确认的边界

- 选卡规则只能决定“先看谁”，不能把弱候选变成好卡
- 热点 lane 还没跑厚，但主线已经够稳，不能为了补热点硬发坏卡
- 当运营队列被“重复候选 + 弱证据 + 正确的废话”占满时，正确动作不是继续发，而是停下来等下一轮 collect

## 下一步

- 继续按当前 `signal-ops` 跑稳态运营
- 继续优先看 `listing-first`
- 继续盯第 `4 / 5` 张真正像样的 `爆贴热点`
- 不再让坏候选反复回到 validate 队列
