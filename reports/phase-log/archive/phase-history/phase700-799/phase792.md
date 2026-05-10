# phase792 - 第四轮供给/编排修复：15/18 离线合同复核与 frontier 确认

## 本轮目标

按 key-os 的第四轮目标，继续不动 prompt、lane 定义、schema，只修并复核离线 planner：

- `limit=15` 继续保持 `publish` 形态
- `limit=18` 清掉 `mcp-workflows` 重复占位
- 确认 frontier 已从 `15` 推到 `18`

## 实际改动

- `backend/app/services/hotpost/offline_publish_plan.py`
  - `hot` 在同 scope 竞争时，优先 `ready draft`
  - `breakdown` 的 pack 去重只在 `target_total <= 15` 时启用
- `backend/tests/services/hotpost/test_offline_publish_plan.py`
  - 新增：
    - `hot` draft 优先测试
    - `breakdown` pack 去重测试

## 验证

### metadata

- `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
- 结果：
  - `changed_items = 0`

### 单测

- `.venv/bin/pytest backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`
- 结果：`5 passed`

### limit=15

- lane：
  - `signal = 9`
  - `hot = 4`
  - `breakdown = 2`
- scope：
  - `ai-automation = 5`
  - `business-growth-ops = 5`
  - `ecommerce-sellers = 5`
- 重点 pack：
  - `business-growth-ops:organic-discovery = 1`
  - `ai-automation:agent-builder = 1`
  - `ecommerce-sellers:selection-signals = 1`
- named topic：
  - `category-demand-shift = 1`
  - `checkout-conversion = 1`
  - `mcp-workflows = 1`

### limit=18

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

- `15` 继续保持 `publish` 形态，lane / scope / named topic 都稳定。
- `18` 这轮已达到合同口径：
  - `10 / 5 / 3`
  - `6 / 6 / 6`
  - `mcp-workflows` 不再重复
- frontier 已从 `15` 继续推进到 `18`。

## release 影响

- 本轮没有重建 release
- 当前 release 仍是：
  - `release-6fb115e4b88a`
