# Phase 623 - 主链 P0 第二刀：并行 Retrieval 接入

时间：2026-03-31 14:50 CST

## 本轮完成

1. `hybrid_retriever` 已支持：
   - 多条英文 `search_queries`
   - 多条 `semantic_queries`
2. `analysis_engine` 已在开放题主链接入并行 retrieval：
   - `search_queries = query_plan.retrieve_queries_en`
   - `semantic_queries = [原始中文 query + retrieve_queries_en]`
3. 保持旧合同不变：
   - 如果没有显式 `search_queries / semantic_queries`
   - 旧的空 token -> `skipped` 行为仍成立

## 当前效果

主链 retrieval 现在不再只押一份 `topic_tokens`。

当前已变成：

- 英文检索式并行全文检索
- 原始中文 query 并行 embedding 检索
- 检索结果继续在同一 hybrid merge 里汇总

## 验证

- `compileall` 通过
- 定向 pytest：
  - `test_hybrid_retriever.py`
  - `test_open_question_query_plan.py`
  - `test_warzone_classifier.py`
  - `test_analysis_engine.py`
- 结果：`59 passed`

## 当前判断

P0 第二刀已经完成。

现在主链中文开放题这条线，P0 剩下的主问题已经收窄到：

1. 漂移保险丝
   - entity preservation
   - invented entity penalty
   - retrieval consistency

## 下一步

P0 第三刀：

1. 加最小漂移保险丝
2. 然后回到 live 验收
3. 看这时剩下的问题是不是已经纯粹是数据与报告质量问题
