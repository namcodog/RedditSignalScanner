# phase838

## 时间
- 2026-04-15

## 背景
- 延续 growth winner path 回灌后的上线前提纯。
- 当前 key-os 口径：
  - 不重开主线实验
  - 不动 `funnel`
  - 只替掉 `organic-discovery` 在 publish 面里的旧 `group breakdown draft`
- 目标 winner：
  - `organic_swap_content_marketing_v2`

## 本轮动作
1. 在 `offline_publish_plan.py` 增加最小 `P1 purity cleanup` 规则：
   - 仅作用于 `business-growth-ops:organic-discovery`
   - 仅当 publish 面里存在旧 `group breakdown draft`
   - 且存在未上屏的 `organic-discovery:listing_keyword_bridge` + `matched_subreddit=content_marketing` 新 candidate
   - 用该 candidate 替换旧位
2. 给 candidate row 补齐：
   - `matched_subreddit`
   - `source_communities`
   - `primary_reason`
   方便验收与后续审计
3. 新增回归测试：
   - `test_growth_purity_cleanup_swaps_stale_organic_breakdown_for_content_marketing_candidate`
4. 回归验证：
   - `pytest ...test_offline_publish_plan.py ...test_topic_metadata.py ...test_reddit_candidate_mapper.py ...test_reddit_search_spec_builder.py ...test_source_scope_candidate_collector.py`

## 结果
- 测试通过：
  - `38 passed`
- 旧 `organic` 位已被替掉：
  - 被替掉的旧位：
    - `draft-group-business-growth-ops-d2d62644cb`
  - 替上来的新位：
    - `cand-business-growth-ops-1skd0vb`
    - subreddit = `content_marketing`
    - title = `Content marketing feels broken in 2026… is anyone actually seeing ROI anymore`

## 最新 publish 面指标
- `organic_new_intake_share = 1.0`
- `organic_old_draft_count = 0`
- `funnel_publish_keyword_count = 3`
- `growth_new_discovery_count = 5`

## 最新 growth 可见层
- `organic-discovery`
  - `cand-business-growth-ops-1sinaiq` (`Blogging`)
  - `cand-business-growth-ops-1skd0vb` (`content_marketing`)
- `funnel-conversion`
  - `cand-business-growth-ops-1sij4bv` (`shopify`)
  - `cand-business-growth-ops-1sh739c` (`ecommerce`)
  - `cand-business-growth-ops-1sm2jgu` (`ecommerce`)

## 判断
- 这轮已经达到 `growth-pack-purity-cleanup-v1` 的 winner 口径：
  - `organic-discovery = 2 新 + 0 旧`
  - `funnel-conversion` 强度不回退
  - growth 可见层新发现感增加
- 但这轮仍然只应表述为：
  - **growth winner path 的上线前提纯**
  - 不应误写成新主线实验

## 变更文件
- `backend/app/services/hotpost/offline_publish_plan.py`
- `backend/tests/services/hotpost/test_offline_publish_plan.py`

## 建议
- 这次 purity cleanup 可以直接带入当前上线版本。
