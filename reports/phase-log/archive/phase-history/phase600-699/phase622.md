# Phase 622 - 主链 P0 第一刀：结构化 Query Plan + Route Top-K 边界

时间：2026-03-31 14:40 CST

## 本轮完成

1. 新增开放题结构化 query plan：
   - [open_question_query_plan.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/analysis/open_question_query_plan.py)
2. `analysis_engine` 已接入 query plan：
   - route 不再只吃散乱 `keywords`
   - 现在会记录：
     - `query_plan`
     - `route margin`
     - `candidate warzones`
3. `WarzoneClassifier` 已支持 ranked candidates
4. `build_open_topic_route()` 已支持：
   - `route_query`
   - Top-K 候选判断
   - margin 太小时不锁定 warzone

## 代码级结果

对 query：

`卖成人用品时，最卡下单成交的地方是什么？我想看看到底是支付、审核还是信任问题卡住了转化。`

当前前段输出为：

- `route_query_en = checkout conversion orders sales`
- `retrieve_queries_en =`
  - `checkout conversion orders`
  - `conversion orders sales`
  - `checkout conversion`
- `route.warzone = Ecommerce_Business`
- `route.margin = 1.0`

## 验证

- `compileall` 通过
- 定向 pytest：
  - `test_open_question_query_plan.py`
  - `test_warzone_classifier.py`
  - `test_analysis_query_support.py`
  - `test_analysis_engine.py`
- 结果：`63 passed`

## 当前判断

这一刀已经把“中文开放题只有一串散乱关键词、route 只能 Top-1 硬锁”的问题拆开了。

但 P0 还没全部完成。

当前仍未完成的是：

1. retrieval 仍然没有做到中文/英文并行多路融合
2. drift guard 还没真正落到：
   - entity preservation
   - invented entity penalty
   - retrieval consistency

## 下一步

P0 第二刀：

1. retrieval 从单份 `topic_tokens` 扩成多条 `retrieve_queries`
2. 把中文原始 query 的作用从末端 evidence filter 往前提
3. 再补最小漂移保险丝
