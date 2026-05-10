# Phase 560 - Rant 路由与迁移信号收口

## 发现了什么？
- `rant` 之前不是“模型弱”，而是没有按独立模式收：
  1. `search_workflow._should_run_reasoning` 先吃 `evidence_count`，`rant` 又不在 trigger list，很多情况根本进不了重模型。
  2. 就算进了 reasoning，`_is_reasoning_candidate_better` 也不会在 `rant` 打平时优先保留重层结果。
  3. `query_planner / retrieval / evidence_package` 已经有严格锚点和 focus 机制，但 `rant` 没真正用起来。
  4. `response_bundle` 把 `competitor_mentions` 直接转成 `migration_intent.destinations`，所以 `that / them / time` 这种脏词会直接穿透到页面。

## 是否需要修复？
- 需要。
- 这一轮不再先动页面，也不先怪模型，先把：
  - 路由
  - 拿料
  - migration fallback
  这三刀收住。

## 精确修复方法
- 更新 `backend/config/hotpost_quality.yaml`
  - `rant` 加入 `reasoning_trigger_modes`
  - `reasoning_min_evidence_by_mode.rant = 8`
  - `strict_domain_terms.rant` + `strict_anchor_min_hits.rant = 1`
  - `evidence_packaging.rant` 改成：
    - `keep_focus_only = true`
    - 更高 `domain_weight`
    - 更高 `min_post_score / min_comment_score`
- 更新 `backend/app/services/hotpost/search_workflow.py`
  - 新增 `rant` 的“成形信号”判断：
    - `pain_points`
    - `top_quotes`
    - `migration_intent`
    - `mode_state`
  - 当这些信号已经成形时，`rant` 不再只看 `evidence_count`
  - `rant` 和 `trending / opportunity` 一样，在快层和重层打平时优先采用重层结果
- 更新 `backend/app/services/hotpost/query_planner.py`
  - 当 `rant` 没命中配置里的 strict terms 时，自动把 query 的问题域词提升成 strict anchors
- 更新 `backend/app/services/hotpost/response_bundle.py`
  - 过滤脏的 migration destinations：
    - 代词 / 时间词
    - `mentions < 2`
    - `sentiment = negative`
  - 没稳定迁移信号时，不再硬塞 `destinations / key_quote`

## 验证
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_runtime_config.py backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_retrieval_precision.py backend/tests/services/hotpost/test_hotpost_search_workflow.py backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_search_service.py -q`
- 结果：`38 passed`
- 兼容补丁后补跑：
  - `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_summary.py::test_build_debug_info_returns_stable_contract backend/tests/services/hotpost/test_hotpost_runtime_config.py backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_retrieval_precision.py backend/tests/services/hotpost/test_hotpost_search_workflow.py backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_search_service.py -q`
  - 结果：`39 passed`
- 扩展回归：
  - `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost -q`
  - 结果：
    - `128 passed`
    - 2 个非本轮引入失败：
      - `test_hotpost_report_llm.py::test_render_hotpost_prompt_contains_inputs`
        - 旧断言仍期待 prompt 包含 `市场趋势分析师`
      - `test_hotpost_repository.py::test_maybe_discover_community_normalizes_name`
        - 本地环境连接 `localhost:5432` 被系统拒绝

## 下一步系统性计划
1. 跑 1-2 条真实 `rant` query，直接看：
   - 是否稳定进 `reasoning`
   - top posts / top quotes 是否更聚焦
   - migration block 是否不再吐脏词
2. 再收页面文案：
   - `迁移信号` -> `有没有人在考虑换掉`
   - `样本不足` -> 更像产品话术
   - `这句话为什么重要` -> `这句话说明了什么`

## 这次执行的价值是什么？
- 这轮把 `rant` 的主因从“感觉浅”收成了可验证的三处代码入口。
- 不是再继续堆 prompt，而是先把：
  - 重模型路由
  - 拿料锚点
  - migration fallback
  这三层拉正。
- 这样下一轮跑真实 `rant` live 时，看到的差异才是有效信号，而不是旧链路噪音。
