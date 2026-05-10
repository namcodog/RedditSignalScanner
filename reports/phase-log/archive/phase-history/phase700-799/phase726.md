# Phase 726 - 采集配额放宽，分离“多抓”和“严发”

## 本轮目标

- 解决“Reddit 很大，但候选池一直只有二十几条”的结构性问题
- 把采集量和发布标准拆开
- 在不回到旧世界的前提下，让系统先多命中帖子，再由 review 严格筛掉坏卡

## 发现

当前主瓶颈不是 Reddit 没料，而是我们自己把进口掐得太小：

- `daily_collect.py` 默认每个 scope 只抓 `8` 条候选
- `source_scope_candidate_collector.py`
  - search / listing 每个 spec 只抓 `3` 条帖子
  - comments 只抓 `5` 条
- YAML 里多个 pack 的 `candidate_cap` 还是 `1` 或 `2`

结果就是：

- 即使上游供给面在变宽
- 真正进入候选池的量还是被前面几层配额压扁

## 关键改动

### 1. 采集默认值改成 YAML 驱动

在 [hotpost_supply_discovery_v2.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_supply_discovery_v2.yaml) 新增：

```yaml
global_rules:
  collect_defaults:
    max_candidates_per_scope: 24
    search_fetch_limit: 12
    listing_fetch_limit: 12
    comments_fetch_limit: 8
```

### 2. pack candidate cap 整体放宽

不改发布规则，只放宽候选进口：

- `upstream-winds: 2 -> 3`
- `tools-efficiency: 1 -> 2`
- `agent-builder: 1 -> 2`
- `selection-signals: 1 -> 3`
- `category-winds: 1 -> 2`
- `paid-economics: 1 -> 2`
- `organic-discovery: 2 -> 3`
- `funnel-conversion: 1 -> 2`

### 3. collector 真正按新配额抓

修改：

- [hotpost_supply_contract.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hotpost_supply_contract.py)
  - 新增 `get_supply_collect_defaults()`

- [hotpost_supply_projection.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hotpost_supply_projection.py)
  - payload 新增：
    - `search_fetch_limit`
    - `listing_fetch_limit`
    - `comments_fetch_limit`

- [source_scope_candidate_collector.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/source_scope_candidate_collector.py)
  - search/listing 不再固定 `3`
  - comments 不再固定 `5`
  - 全部改成读 YAML

- [daily_collect.py](/Users/hujia/Desktop/RedditSignalScanner/backend/scripts/hotpost/daily_collect.py)
  - 默认 `--max-candidates` 改成读 YAML `24`

## 当前结论

- 这次不是放松质量闸门
- 是把“多抓帖子”和“严发卡片”真正拆开了

也就是说，后面应该出现的状态是：

- 候选池明显变厚
- review 继续严
- 不会因为入口变宽，就把情绪帖和正确废话直接推上前台

## 验证

- `pytest backend/tests/services/hotpost/test_source_scope_candidate_collector.py backend/tests/services/hotpost/test_source_scope_catalog.py backend/tests/services/hotpost/test_reddit_search_spec_builder.py -q`
  - `18 passed`
- `python -m py_compile backend/app/services/hotpost/source_scope_candidate_collector.py backend/app/services/hotpost/hotpost_supply_projection.py backend/app/services/hotpost/hotpost_supply_contract.py backend/scripts/hotpost/daily_collect.py`
  - 通过

## 下一步

1. 用这份新配额重跑 collect
2. 看候选池是不是从当前二十几条明显抬升
3. 再按现有 `signal-ops / hot-ops` 严格出卡，不为补量回退口径

## 2026-04-09 当轮验证结果

- 放宽前候选池：
  - `before_total = 51`
  - `AI = 23`
  - `电商 = 20`
  - `增长 = 8`
- 只重跑 `business-growth-ops --max-candidates 24` 后：
  - `after_total = 67`
  - `AI = 23`
  - `电商 = 20`
  - `增长 = 24`

也就是说，这次不是“改了配置但没效果”，而是**最薄的增长线已经从 `8` 条候选抬到 `24` 条，直接吃满新配额**。

新的 validate 队列里已经能看到更宽的料面，例如：

- `Gemma 4 has been released`
- `Amazon Just Announced 3.5% Tax on FBA fees`
- `SEMRush charged me $211 using deceptive dark patterns`
- `How much content do I actually need before launching a new site?`
- `SEO vs AEO`

结论：

- 采集进口放宽已经生效
- 现在真正该做的是继续补 `AI / 电商` 两条线的 collect，而不是放松发布闸门
