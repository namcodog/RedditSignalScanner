# phase837

## 时间
- 2026-04-15

## 背景
- 延续 `phase836` 的 growth intake path 回灌审计。
- 上一轮确认：
  - growth winner path 已进主链
  - 但 `winner-equivalent` 结论写过满
  - 真正阻塞点不是 matcher 社区面本身，而是 `sync_topic_metadata` 会把 `funnel-conversion:listing_keyword_bridge` 候选语义覆盖回 `paid-economics`

## 本轮动作
1. 对 `topic_metadata.py` 做最小对齐：
   - 仅对 `business-growth-ops`
   - 仅对 `organic-discovery / funnel-conversion`
   - 仅对 `*:listing_keyword_bridge`
   - 禁止 metadata 再次语义改包
2. 新增回归测试：
   - `test_resolve_topic_metadata_preserves_growth_listing_bridge_pack`
3. 重跑：
   - `pytest tests/services/hotpost/test_topic_metadata.py tests/services/hotpost/test_reddit_candidate_mapper.py tests/services/hotpost/test_reddit_search_spec_builder.py tests/services/hotpost/test_source_scope_candidate_collector.py -q --tb=short`
   - `sync_topic_metadata.py --json`
   - `run_offline_publish_plan.py --limit 15`

## 结果
- 测试通过：
  - `30 passed`
- metadata 覆盖问题已修复：
  - `cand-business-growth-ops-1sm2jgu`
    - `paid-economics -> funnel-conversion`
    - `cluster = funnel`
- 最新 `offline_publish_plan-15` 中，目标 pack publish 面为：
  - `organic-discovery = 2`
    - `1 hot candidate`
    - `1 breakdown draft`
  - `funnel-conversion = 3`
    - `3 signal candidates`
- 目标 pack 直接候选进入 publish 的社区来源为：
  - `Blogging`
  - `shopify`
  - `ecommerce`
- 关键口径：
  - `target_candidate_new_subreddit_count = 3`
  - `direct_candidate_publish_count = 4`

## 判断
- 这轮不是全量复刻 key-os winner。
- 但项目侧已经从“directionally successful”推进到：
  - **target-pack publish new_subreddit_count 达到 3**
  - **funnel-conversion 不再只靠 ecommerce**
- 所以当前更准确的结论是：
  - winner path 已进主链：是
  - target-pack publish 面达到本轮最低 winner 线：是
  - 完整 winner-equivalent：仍不应写死

## 变更文件
- `backend/app/services/hotpost/topic_metadata.py`
- `backend/tests/services/hotpost/test_topic_metadata.py`

## 下一步
- 继续盯 `organic-discovery` 的直接 candidate -> publish 厚度
- 不改 prompt / planner / frontend / named topic / schema
- 后续 phase 结论必须区分：
  - `target-pack metrics`
  - `global publish metrics`
