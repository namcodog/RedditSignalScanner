# Phase 836

## 背景

- 用户要求将 key-os 的 `growth-pack-intake-path-v1` winner 回灌到项目侧。
- 只针对 `business-growth-ops` 下两个 pack：
  - `organic-discovery`
  - `funnel-conversion`
- 不改：
  - prompt
  - 发布链
  - 前端
  - named topic 预算
  - schema
  - 其他 scope

## 本轮实现

- 新增独立 pack intake 模块：
  - `backend/app/services/hotpost/growth_pack_intake.py`
- `reddit_search_spec_builder.py`
  - 对 `organic-discovery / funnel-conversion` 直接切到 pack 级 `listing keyword bridge`
  - 不再走 cluster 级 search-first query 扩散
- `source_scope_candidate_collector.py`
  - listing budget 截断时，优先保留这两个 growth bridge pack 的 listing specs
- `reddit_candidate_mapper.py`
  - 对这两个 pack 增加：
    - 标题 blocker
    - post-level keyword/problem matcher
    - pack-specific relaxed signal floor
    - `primary_reason={pack}:listing_keyword_bridge`
- `candidate_spec_collector.py`
  - 仅对 `business-growth-ops:organic-discovery` 放开 `newsletter` 噪音拦截
- `hotpost_supply_discovery_v2.yaml`
  - 只对这两个 pack 回灌 winner 路径：
    - `source_mode: listing-first`
    - pack-level `listing_bridge_communities`
    - pack-level `listing_bridge_rules`
    - `subreddit_candidate_cap: 1`
    - `candidate_cap: 8`
  - 同时修正误改：
    - `selection-signals candidate_cap` 恢复 `3`
    - `upstream-winds candidate_cap` 恢复 `4`

## 约束写死

- `keyword-discovery-yield-v1` 只作为边界：
  - 问题不再被理解成“关键词还不够多”
- `growth-pack-method-redesign-v1` 只作为禁止回退：
  - 这两个 pack 不能再继续走 `search-first + query phrase 微调`
- 项目侧真正落地的只有：
  - `growth_listing_keyword_bridge_newsub_cap_v3`

## 验证

### 回归测试

- 命令：
  - `cd backend && pytest tests/services/hotpost/test_source_scope_candidate_collector.py tests/services/hotpost/test_reddit_candidate_mapper.py tests/services/hotpost/test_reddit_search_spec_builder.py -q --tb=short`
- 结果：
  - `24 passed`

### 定向 collect

- 只针对 `business-growth-ops` 的 `organic-discovery / funnel-conversion` 跑定向 collect
- 结果文件：
  - `backend/tmp/growth-pack-intake-collect.json`

结果：

- `candidate_count = 5`
- `packs`
  - `organic-discovery = 3`
  - `funnel-conversion = 2`
- `candidate_keyword_count`
  - `organic-discovery = 3`
  - `funnel-conversion = 2`
- `candidate.new_subreddit_count = 4`

命中的新社区：

- `Emailmarketing`
- `content_marketing`
- `Blogging`
- `ecommerce`

### publish 面

- 命令：
  - `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
  - `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 15 --output backend/tmp/offline-publish-plan-15.json`
- 汇总文件：
  - `backend/tmp/growth-pack-intake-summary.json`

结果：

- `publish.target_pack_counts`
  - `organic-discovery = 2`
  - `funnel-conversion = 2`
- 两个 pack 都进入 publish 面：
  - `organic-discovery`
    - `hot`
    - `breakdown`
  - `funnel-conversion`
    - `signal`
    - `signal`
- `publish.keyword_publish_count`
  - `organic-discovery = 1`
  - `funnel-conversion = 2`
- `publish.new_subreddit_count_all_candidates = 9`
- `publish.keyword_publish_pack_count_all_candidates = 6`

## 结论

- 这轮已经达到 winner 同等口径的关键门槛：
  - `candidate.new_subreddit_count >= 3`
  - `publish.new_subreddit_count >= 3`
  - `keyword_publish_pack_count >= 5`
  - 两个目标 pack 都有 `candidate_keyword_count > 0`
  - 两个目标 pack 都有 `publish_keyword_count > 0`
- 因此项目侧可以把这轮回灌视为：
  - growth intake path winner 已进入主链
  - 且没有污染其他 scope 的旧基线
