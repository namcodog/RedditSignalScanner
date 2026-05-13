# Phase 626 - 跨领域开放题 live 复验：Family 通过，EDC 仅剩证据链接尾巴

## 已完成

1. 重启 live runtime，确认当前验收环境恢复正常
   - `backend` / `analysis-live` / `bulk-live` 全部正常
2. 复验 `Family_Parenting` 开放题
   - 先暴露出一层真问题：
     - `open_topic_route` 本身是对的
     - 但 `drift_guard` 的 `retrieval_consistency` 在 Family 题材上误伤，过早放松了 route
   - 修复后重新 live：
     - `accepted = 1/1`
     - `report_tier = A_full`
3. 复验 `Tools_EDC` 开放题
   - route / query plan / retrieval 都稳定
   - 最终 `report_tier = A_full`
   - 但验收仍失败，原因只剩：
     - `opportunity evidence has no clickable reddit link`
     - `reddit evidence links insufficient: 1 < 2`

## 关键改动

1. 修改：
   - `backend/app/services/analysis/open_question_drift_guard.py`
2. 新增测试：
   - `backend/tests/services/analysis/test_open_question_drift_guard.py`
   - 新覆盖：
     - Family 题材在强 route / 高 margin / 已有 route_hits 的情况下，不应因泛社区噪音被误松 route

## 验证

1. 定向回归：
   - `pytest tests/services/analysis/test_open_question_drift_guard.py tests/services/analysis/test_analysis_engine.py tests/services/analysis/test_open_question_query_plan.py tests/services/semantic/test_hybrid_retriever.py -q`
   - `62 passed`
2. Family live：
   - 失败样本（暴露误伤）：
     - `backend/reports/local-acceptance/open_question_live_final_1775133960.json`
   - 修复后通过样本：
     - `backend/reports/local-acceptance/open_question_live_final_1775134610.json`
     - `accepted = 1/1`
     - `report_tier = A_full`
3. EDC live：
   - `backend/reports/local-acceptance/open_question_live_final_1775134686.json`
   - `report_tier = A_full`
   - 但 `accepted = 0/1`
   - 原因：
     - 可点击 Reddit 证据链接不足（`1 < 2`）

## 新结论

1. 当前主链前段已经具备跨领域稳定性
   - `Family_Parenting`：route 修正后重新回到 `A_full`
   - `Tools_EDC`：route / retrieval / facts quality 仍保持 `A_full`
2. `Family` 这次失败不是 route 产不出来，而是 `drift_guard` 对高置信 Family 路线误伤
3. `EDC` 当前剩余问题不是前段，不是质量门槛，而是输出层证据链接密度不足
4. 所以现在主链剩余问题已经进一步收窄：
   - 不是 DB
   - 不是语义库
   - 不是中文 route
   - 而是少数题材上的证据链接合同还没完全稳住

## 下一步

1. 直接收 `EDC` 这类题材的 evidence link density
   - 为什么 `report_tier = A_full` 但只有 `1` 条可点击 Reddit 链接
2. 补 `analyses.sources` 的审计可读性
3. 然后再决定是否扩到第三个领域复验
