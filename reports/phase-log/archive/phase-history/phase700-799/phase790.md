# phase790 - 第二轮供给/编排修复：pack 露出与 named topic 去重

## 本轮目标

按 key-os 的第二轮 supply/programming 结论，继续修离线编排投影：

- 不改 prompt
- 不改 lane 定义
- 不改 schema
- 只修：
  - `limit=12/15` 下的 pack 露出
  - `single_named_topic_overflow`

## 实际改动

- `backend/app/services/hotpost/offline_publish_plan.py`
  - 新增 pack programming target 常量
  - 新增 named topic budget 常量
  - `scope_targets` 改为按窗口缩放，不再固定吃 `10/10/10`
  - planner 维护 `pack_counts / named_topic_counts`
  - `_take_from_pool()` 与 remainder 追加都接入 named topic 去重
  - `_plan_sort_key()` 改成：
    - 先看 `scope_gap`
    - 再看 `pack_gap`
    - 保持其余排序尽量稳定
  - 新增：
    - `_resolve_scope_targets()`
    - `_resolve_pack_targets()`
    - `_resolve_scaled_targets()`
    - `_apply_selection()`
    - `_can_take_named_topic()`
- `backend/tests/services/hotpost/test_offline_publish_plan.py`
  - 新增 `single_named_topic_max=1` 的回归测试

## 本轮没有改

- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/app/services/hotpost/reddit_search_spec_builder.py`
- `backend/app/services/hotpost/named_topic_watchlist.py`
- `backend/app/services/hotpost/named_topic_candidate_collector.py`
- 任意 prompt / lane 定义 / schema

原因：

- 第一轮补货后，本地库存已经足够
- 第二轮真正的瓶颈不是“继续补库存”，而是 planner 没把库存正确投影出来

## 验证

### metadata 同步

- `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
- 结果：
  - candidates: `28`
  - drafts: `38`
  - published: `155`
  - 本轮 `changed_items = 0`

### 单测

- `.venv/bin/pytest backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`
- 结果：`3 passed`

### limit=12 离线计划

- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 12 --output backend/tmp/offline-publish-plan-12.json`
- lane：
  - `signal = 7`
  - `hot = 3`
  - `breakdown = 2`
- scope：
  - `ai-automation = 4`
  - `business-growth-ops = 4`
  - `ecommerce-sellers = 4`
- pack：
  - `ai-automation:agent-builder = 1`
  - `business-growth-ops:organic-discovery = 1`
  - `ecommerce-sellers:selection-signals = 1`
- named topic：
  - `checkout-conversion = 1`
  - `category-demand-shift = 1`
  - `mcp-workflows = 1`

### limit=15 离线计划

- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 15 --output backend/tmp/offline-publish-plan-15.json`
- lane：
  - `signal = 9`
  - `hot = 4`
  - `breakdown = 2`
- scope：
  - `ai-automation = 5`
  - `business-growth-ops = 5`
  - `ecommerce-sellers = 5`
- pack：
  - `ai-automation:agent-builder = 1`
  - `ecommerce-sellers:selection-signals = 2`
  - `business-growth-ops:organic-discovery = 0`
- named topic：
  - `checkout-conversion = 1`
  - `category-demand-shift = 1`
  - `mcp-workflows = 1`

## 结论

- `limit=12`
  - lane 对齐
  - scope 对齐
  - 三个重点 pack 都已经进入 `publish_list`
- `limit=15`
  - lane 对齐
  - scope 对齐
  - `single_named_topic_overflow` 已消失
  - `checkout-conversion` 不再重复两次
  - 新瓶颈前移到：
    - `business-growth-ops:organic-discovery` 在 `15` 张窗口里会被 `breakdown` 稀缺坑位挤掉

## release 影响

- 本轮没有重建 release
- 当前 release 仍是：
  - `release-6fb115e4b88a`
