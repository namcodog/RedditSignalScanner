# Phase 621 - 中文开放题 CLIR / 路由漂移架构评估

时间：2026-03-31 14:20 CST

## 结论

用户提出的判断方向是对的：当前主链真正的问题不是“中文不行”，而是中文开放题进入主链后，`query framing -> route -> retrieve` 这一前段链路仍然过于串行，前面一旦偏，后面会跟着偏。

但当前系统也不是完全“单链到底”。现状更准确的描述是：

- 前段：
  - `product_description + keywords`
  - `build_open_topic_route()`
  - `WarzoneClassifier` 输出 Top-1 `warzone`
  - 社区池按 `warzone` 和 `seed_profiles` 先缩窄
- 中段：
  - `run_hybrid_retrieval()` 做英文 `websearch_to_tsquery` 全文检索 + embedding 检索
  - 两路结果按加权分数融合，不是 `RRF`
- 后段：
  - `apply_query_focus_filter()` / `select_evidence_posts()` 会重新看原始中文 `product_description`
  - 属于末端证据过滤，不是独立跨语言 reranker

## 代码级确认

### 1. 当前确实存在“前段早锁”

- `build_open_topic_route()` 会把 `product_description + keywords` 拼成一份 `route_text`
- `WarzoneClassifier.classify_texts()` 只返回一个 Top-1 `warzone`
- `_filter_communities_for_open_topic_route()` 会先按 `warzone / seed_profiles` 过滤社区

这说明：
- route 仍是单候选
- 没有 `Top-K route`
- 没有 `route margin`
- 也没有“Top1 和 Top2 太近时不锁社区”的保险丝

### 2. 当前 retrieval 不是纯 semantic，但还不是用户建议的并行 CLIR

`run_hybrid_retrieval()` 现在是：
- 英文 fulltext：`websearch_to_tsquery('english', :search_query)`
- embedding retrieval：`post_embeddings`
- 用线性加权分数融合

这说明：
- 不是只押 semantic
- 也不是中文/英文并行检索
- 不是 `BM25 + multilingual embedding + RRF`
- 仍然主要依赖英文化后的 `topic_tokens`

### 3. 当前末端已经有一点“中文回看”

`select_evidence_posts()` 会使用：
- `product_description`
- `keywords`
- `route_reasons`
- `preferred_communities`

所以系统不是完全忽略原始中文，而是：
- 原始中文主要在末端证据筛选层生效
- 没有在 route / retrieval 前段承担足够强的约束

## 对用户方案的评估

### 应该直接采纳（P0）

1. 不再输出“一条自由英文句子”，而是结构化 rewrite 对象
   - 拆出：
     - `route_query`
     - `retrieve_queries`
     - `rerank_query`
     - `must_keep`
     - `must_not_invent`

2. route 改成 `Top-K + margin`
   - 不再 Top-1 直接锁死

3. retrieval 改成“中文 + 英文并行”
   - 至少应有：
     - 中文 query 路
     - 英文 query 路
     - 关键词全文检索路

4. 加漂移保险丝
   - `entity preservation`
   - `invented entity penalty`
   - `route margin`
   - `retrieval consistency`

### 现在不该立刻做（P1/P2）

1. `back-translation check`
   - 值得做，但不是第一刀

2. 历史点击/满意度训练 router
   - 现在还太早

3. 全量双语 corpus 扩充
   - 当前成本过大，容易重新把项目拖进大改造

## 当前优先级判断

“中文偏差”的准确说法应该是：

> 不是中文翻译错了，而是主链对中文开放题的结构化理解、路由决策和召回方式还不够解耦。

所以当前主链第一优先级，应该是：

1. 结构化 rewrite（受约束改写）
2. route Top-K 化
3. 中文/英文并行 hybrid retrieval
4. 漂移保险丝

而不是继续只补 anchor 或继续打单题 patch。
