# phase736

## 本轮目标

对 hot / supply / lane 做一层深度审计，不继续粉饰“规则已经清楚”，把真正错位的地方全部摊开。

## 发现

1. `hot` 仍被“检索方式”过早拦截
   - `card_lane_policy.py` 里 `search` 候选只要 pack 没开 `allow_search_hot`，会直接回 `signal`
   - 这是把 `search/listing` 当成了帖子性质，不是检索方式

2. `hot` 会被 `signal` 门禁二次误伤
   - `review_queue_policy.py`
   - `card_content_generator.py`
   - 两处都对所有 `validate` 统一走 `assess_signal_input_quality`
   - `hot = validate + lane=hot`，所以也被 `signal` 规则挡

3. “R站老炮儿” prompt 只进了写卡层，没进判断层
   - 只在 `card_content_prompts.py / card_content_generator.py` 使用
   - 没进 collect / lane / queue / review 调度

4. lane mix 目标没真正进调度器
   - 我们定的是最近 20 张 `10 / 6 / 4`
   - 但 `card_selection_policy.py` 仍然只看全历史 scope share
   - 还把领域目标硬编码在 Python 里

5. `breakdown` 目前没有独立供给恢复机制
   - `materialize_breakdown_drafts.py` 本轮没有长出新 write draft
   - 最近 20 张里 `breakdown = 0`

6. `agent-builder` 之前吸走了本该进入 `upstream-winds` 的“开源路线/项目争论”
   - 已做一个窄修：把 `open-source-projects` 从 `agent-builder` 挪掉
   - 回归 `24 passed`

## 产物

- 审计文档：
  - `docs/superpowers/specs/2026-04-09-hot-supply-and-lane-audit.md`

## 本轮价值

这轮不是又改一点规则，而是把系统真正的错位点讲透了：

- 不是 Reddit 不够
- 不是 prompt 不够
- 是判断层和运营层还没按产品定义工作
