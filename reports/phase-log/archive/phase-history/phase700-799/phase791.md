# phase791 - 第三轮供给/编排修复：15 稳住，18 推通

## 本轮目标

第三轮继续不动 prompt、不动 lane 定义、不动 schema，只修离线 planner：

- 让 `limit=15` 继续改善 pack 露出
- 把 frontier 从 `15` 往 `18` 推
- 重点压掉 `mcp-workflows = 2`

## 实际改动

- `backend/app/services/hotpost/offline_publish_plan.py`
  - `hot` 选卡改成更明确的 `draft first`
    - 同 scope 竞争时，ready draft 优先于 raw candidate
  - `breakdown` 的 pack 去重只在 `target_total <= 15` 时启用
    - `15` 继续优先不同 pack，保证 `organic-discovery`
    - `18` 不再硬压不同 pack，让 ecom scope 能补满
- `backend/tests/services/hotpost/test_offline_publish_plan.py`
  - 新增：
    - `breakdown` 优先不同 pack
    - `hot` 在同 scope 下优先 ready draft

## 本轮没有改

- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/app/services/hotpost/reddit_search_spec_builder.py`
- `backend/app/services/hotpost/named_topic_watchlist.py`
- `backend/app/services/hotpost/named_topic_candidate_collector.py`
- 任意 prompt / lane 定义 / schema

## 验证

### metadata 同步

- `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
- 结果：
  - `changed_items = 0`

### 单测

- `.venv/bin/pytest backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`
- 结果：`5 passed`

### limit=15

- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 15 --output backend/tmp/offline-publish-plan-15.json`
- lane：
  - `signal = 9`
  - `hot = 4`
  - `breakdown = 2`
- scope：
  - `ai-automation = 5`
  - `business-growth-ops = 5`
  - `ecommerce-sellers = 5`
- 三个重点 pack 全部进入 `publish_list`：
  - `business-growth-ops:organic-discovery = 1`
  - `ai-automation:agent-builder = 1`
  - `ecommerce-sellers:selection-signals = 1`
- named topic：
  - `category-demand-shift = 1`
  - `checkout-conversion = 1`
  - `mcp-workflows = 1`

### limit=18

- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 18 --output backend/tmp/offline-publish-plan-18.json`
- lane：
  - `signal = 10`
  - `hot = 5`
  - `breakdown = 3`
- scope：
  - `ai-automation = 6`
  - `business-growth-ops = 6`
  - `ecommerce-sellers = 6`
- named topic：
  - `category-demand-shift = 1`
  - `checkout-conversion = 1`
  - `mcp-workflows = 1`
- 不再触发：
  - `named_topic_overflow`
  - `single_named_topic_overflow`
  - `named_topic_share_overflow`

## 结论

- `15` 已经从上一轮的“继续 rewrite”推进到更稳的 publish 形态：
  - lane / scope 继续对齐
  - 三个重点 pack 全部露出
- `18` 这轮已经推通：
  - lane 对齐
  - scope 对齐
  - `mcp-workflows` 不再重复占位
  - named topic budget 全通过

## release 影响

- 本轮没有重建 release
- 当前 release 仍是：
  - `release-6fb115e4b88a`
