# Phase 624 - 主链 P0 第三刀收口：drift guard 与 live 复验

## 已完成

1. 漂移保险丝已与主链 route 社区过滤口径对齐
   - `open_question_drift_guard` 不再只认 `allowed_names`
   - 现在也认当前 route 已放行的同 `warzone` 社区 profile
2. `analysis_engine` 已把当前 `all_communities` 传给 drift guard
3. 已补一条定向测试，覆盖：
   - `r/FacebookAds`
   - `r/buhaydigital`
   这类电商相邻社区不应被误判成 route 外部

## 验证

1. 定向回归：
   - `pytest tests/services/analysis/test_open_question_drift_guard.py tests/services/analysis/test_open_question_query_plan.py tests/services/analysis/test_analysis_engine.py tests/services/semantic/test_hybrid_retriever.py -q`
   - `61 passed`
2. 编译检查：
   - `python -m compileall app/services/analysis/open_question_drift_guard.py app/services/analysis/analysis_engine.py`
3. live preflight：
   - `ok=true`
   - `enabled_registry_count=160`
   - `recent_posts_count=1686`
   - `recent_posts_with_semantic_count=104`
4. live 复验：
   - 结果文件：
     - `backend/reports/local-acceptance/open_question_live_final_1774941936.json`
   - 最终：
     - `accepted=0/1`
     - `report_tier=B_trimmed`

## 新结论

1. P0 漂移保险丝已经收住
   - route 没再被 retrieval 误松掉
   - `open_topic_route.warzone=Ecommerce_Business`
   - `drift_guard.retrieval.relax_route=false`
2. 当前 live 剩余主问题已经变成报告质量问题，不再是前段 route 漂移
3. 本轮 live 的真实阻塞是：
   - `facts_flags=['solutions_low', 'coverage_partial']`
4. 命中的社区盘已稳定留在电商盘：
   - `r/ecommerce`
   - `r/dropshipping`
   - `r/shopify`
   - `r/SaaS`

## 下一步

1. 不再继续扩主链 CLIR P0
2. 切到报告主链质量：
   - 为什么 `coverage_partial`
   - 为什么 `solutions_low`
3. 用当前已稳住的 route/query/retrieval 前段，继续做跨领域复验
