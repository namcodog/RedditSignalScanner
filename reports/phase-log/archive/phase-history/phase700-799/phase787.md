# phase787

## 主题元数据透传与离线发布 dry-run

### 本轮目标

- 给 hotpost 卡片结构补齐并透出：
  - `topic_pack_id`
  - `topic_cluster_id`
  - `topic_cluster_ids`
  - `named_topic_ids`
- 确保字段进入：
  - `candidates`
  - `review_queue`
  - `releases`
  - `mini_snapshots`
- 提供本地离线发布计划 dry-run，不调用 Reddit API。

### 实际改动

- schema：
  - `backend/app/schemas/hotpost_source_scopes.py`
  - `backend/app/schemas/hotpost_card_candidates.py`
  - `backend/app/schemas/hotpost_card_drafts.py`
  - `backend/app/schemas/hotpost_clues.py`
- 数据流：
  - `backend/app/services/hotpost/reddit_search_spec_builder.py`
  - `backend/app/services/hotpost/reddit_candidate_mapper.py`
  - `backend/app/services/hotpost/card_draft_builder.py`
  - `backend/app/services/hotpost/card_group_draft_builder.py`
  - `backend/app/services/hotpost/named_topic_watchlist.py`
  - `backend/app/services/hotpost/named_topic_candidate_collector.py`
- 新增能力：
  - `backend/app/services/hotpost/topic_metadata.py`
  - `backend/app/services/hotpost/offline_publish_plan.py`
  - `backend/scripts/hotpost/sync_topic_metadata.py`
  - `backend/scripts/hotpost/run_offline_publish_plan.py`
- 测试：
  - `backend/tests/services/hotpost/test_reddit_search_spec_builder.py`
  - `backend/tests/services/hotpost/test_named_topic_candidate_collector.py`
  - `backend/tests/services/hotpost/test_topic_metadata.py`
  - `backend/tests/services/hotpost/test_offline_publish_plan.py`

### 验证结果

- 定向测试：
  - `14 passed`
- 本地回填：
  - `candidates 15/15`
  - `drafts 38/38`
  - `published 155/155`
- review queue 快照：
  - `queue-20260412163958-a760cdb7`
- 新 release：
  - `release-6fb115e4b88a`
- release 检查：
  - `card_count = 155`
  - `feed_contract = 30/30`
  - `cloud_db copy guard: ok`

### 样本核对

- `candidates` 样本已带：
  - `topic_pack_id`
  - `topic_cluster_id`
  - `topic_cluster_ids`
  - `named_topic_ids`
- `review_queue` 样本已带上述字段
- `releases` / `mini_snapshots` / `cloud_db` 样本已带上述字段
- 离线发布计划 JSON：
  - `backend/tmp/offline-publish-plan.json`

### 结论

- 题材元数据透传已正式可用
- 离线发布 dry-run 已正式可用
- 不涉及 prompt、lane 定义或 schema 扩张之外的业务回灌
