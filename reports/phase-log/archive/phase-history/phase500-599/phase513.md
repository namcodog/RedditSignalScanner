# Phase 513 - Hotpost 第二刀：接入 query planner，并收口首轮检索策略

## 本轮目标

按 Phase 511/512 的顺序，继续推进第二刀：

- 给 Hotpost 增加真正的 query planner 合同
- 让 planner 真正接入 `search_workflow`
- 把 query 规划结果写进 `debug_info`
- 保持首轮检索可控，不把延迟炸穿

## 已完成

### 1. 新增 Query Planner

新增：

- `backend/app/services/hotpost/query_planner.py`

planner 当前输出：

- `query_intent`
- `core_terms`
- `expanded_terms`
- `negative_terms`
- `candidate_subreddits`
- `search_strategy`
- `query_parts`

当前口径：

- `trending` -> `trend_tracking`
- `rant` -> `pain_point_discovery`
- `opportunity` -> `opportunity_discovery`

planner 的行为来自配置，不走代码硬写。

### 2. 配置真相源已补齐

已更新：

- `backend/config/hotpost_quality.yaml`
- `backend/app/services/hotpost/hotpost_config.py`

新增配置块：

- `query_resolution.query_planner`

当前收口的配置项：

- `max_query_parts`
- `max_expanded_terms`
- `max_negative_terms`
- `noise_terms`
- `strategy_by_mode`
- `intent_labels`
- `mode_terms`
- `candidate_subreddits`

### 3. Query Planner 已接入 Search Workflow

已修改：

- `backend/app/services/hotpost/search_workflow.py`

当前行为：

- 先做 `resolve_query`
- 再基于 mode + resolution 生成 `query_plan`
- 首轮 evidence collection 直接吃：
  - `query_plan.core_terms`
  - `query_plan.query_parts`
  - `query_plan.candidate_subreddits`（仅 `subreddit-first` 模式）

关键收口：

- 不再对所有模式都强行用候选社区做初始搜索
- 只有 `search_strategy == subreddit-first` 时，才把 `candidate_subreddits` 送进首轮 collection
- 这样避免 `trending` 首轮检索被 planner 直接拖进过重的 subreddit fanout

### 4. Debug 合同已补 query planner 可观测字段

已修改：

- `backend/app/schemas/hotpost.py`
- `backend/app/services/hotpost/response_bundle.py`
- `backend/app/services/hotpost/hotpost_deps_factory.py`

新增 debug 字段：

- `query_intent`
- `expanded_terms`
- `negative_terms`
- `candidate_subreddits`
- `search_strategy`

这意味着后面看 live 结果时，不再只知道“搜了什么”，还知道：

- 为什么这么搜
- 扩了哪些词
- 扔掉了哪些噪音词
- 本来准备去哪几个社区

## 测试

### 新增 / 调整

- 新增：
  - `backend/tests/services/hotpost/test_hotpost_query_planner.py`
- 更新：
  - `backend/tests/services/hotpost/test_hotpost_search_workflow.py`
  - `backend/tests/services/hotpost/test_hotpost_schema.py`

### 验证结果

定向：

```bash
cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_schema.py tests/services/hotpost/test_hotpost_runtime_config.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_query_resolver.py -q
```

结果：

- `24 passed`

全 Hotpost 回归 + acceptance 单测：

```bash
cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost tests/scripts/acceptance/test_run_hotpost_quality_smoke.py -q
```

结果：

- `92 passed`

## live 观察

本轮 live 没有拿到完整质量结论，但暴露了一个真实运行态问题：

- 在当前代理环境下，`/api/hotpost/search` 的真实抓取链路仍然偏重
- `trending` 单题直打在 `60s` 窗口内没有返回

当前判断：

- 第二刀已经把 query planner 接进来了
- 但真实环境的瓶颈已经开始从“query 太弱”切到“首轮 live 抓取延迟仍重”

所以第三刀不能只盯质量，也要一起收 runtime latency

## 当前价值

这轮的价值不是“又多了几个字段”，而是：

- Hotpost 终于开始显式表达 query planning
- 后续可以真正区分：
  - 是 query 规划错了
  - 是召回弱了
  - 还是运行时太慢了

## 下一步

第三刀建议收两件事：

1. query planner 与 recall 解耦
   - 首轮只跑轻 query
   - 扩 query / 扩社区下沉到补证回合
2. runtime latency 收口
   - 限制首轮 external fanout
   - 给 low-cost smoke 增超时内统计
   - 把“结果质量”和“首轮时延”一起验

## 一句话结论

Hotpost 第二刀已经落地：**query planner 有合同、有配置、进主链、可观测。**
但真实环境下一层问题也已经露头：**首轮 live 抓取仍然偏重，下一步必须把质量和时延一起收。**
