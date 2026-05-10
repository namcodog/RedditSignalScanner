# Phase 549 - Hotpost Trending 关键词口径校正（AIGC）

## 时间
- 2026-03-28

## 发现了什么
1. `AIGC` 在中文互联网很热，但 Reddit 里并不常直接用这个词。
2. 之前 Hotpost 对 `AIGC` 的首轮搜索，实际还是拿原词去撞 Reddit。
3. 即使已经加了别名扩展，如果首轮 query part 名额只有 1 个，而原词仍排第一，结果还是会继续 miss。
4. 同时，`AIGC` 旧 no-result 结果还被 Redis 缓存着，会继续污染新查询。

## 是否需要修复
- 需要。
- 这不是 Reddit 没数据，而是我们的 `trending` 检索口径没有对齐 Reddit 语境。

## 精确修复方法
### 1. 配置化别名扩展
- 在 `backend/config/hotpost_quality.yaml` 新增：
  - `query_resolution.query_planner.term_aliases.aigc`
  - 值为：
    - `generative ai`
    - `ai-generated content`
    - `gen ai`

### 2. query planner 产出 alias_terms
- `backend/app/services/hotpost/query_planner.py`
- 新增 `alias_terms`
- `expanded_terms` 现在会带上 Reddit 常用别名

### 3. 首轮搜索优先用别名
- `backend/app/services/hotpost/query_planner.py`
- `backend/app/services/hotpost/search_workflow.py`
- 现在首轮 query parts 会优先吃 alias，再补原始 query
- 目的：在 guardrail 限制首轮只跑 1 条时，先用 Reddit 真正常用的叫法去搜

### 4. 清理旧缓存
- 精准清掉 `AIGC` 对应的 Redis 缓存
- 避免旧 no-result 持续覆盖新规则

## 验证
- `pytest backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_runtime_config.py -q` -> `6 passed`
- `pytest backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q` -> `13 passed`
- 运行时最小验证：
  - `build_hotpost_query_plan("AIGC")` 产出：
    - `alias_terms = ["generative ai", "ai-generated content", "gen ai"]`
  - 工作流首轮有效 query part：
    - `generative ai`

## 这次执行的价值
- 把“中文互联网热词”和“Reddit 原生用词”对齐了。
- 以后像 `AIGC` 这种词，不会再被当成 Reddit 原词直接去撞。
- 这一步修的是算法口径，不是补 UI 文案。
