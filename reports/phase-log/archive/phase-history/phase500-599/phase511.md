# Phase 511 - EDC open question live final 收口

时间：2026-03-27

## 本轮目标

把 EDC 开放题从“错赛道样本 + 脏证据 + 过严品牌门禁导致 B_trimmed”收口成真实的 `A_full` live 结果。

## 发现的问题

1. `open_topic_route` 只收住了社区选择层，没有真正下沉到帖子样本层。
   - `Analysis.sources.communities` 已经是 EDC 社区
   - 但 `facts_snapshot.v2_package.sample_posts_db` 里仍混入 `r/startups / r/entrepreneur / r/saas / r/ecommerce`
2. 关键词停用词合同没有和默认停用词合并，导致 `reddit / product` 这类脏词进入 `fetch_keywords` 与 hybrid query。
3. 证据排序会把 “I analyzed X reddit discussions ...” 这类元分析帖塞进 example posts。
4. 在样本、痛点、方案都已达标时，开放式探索题仍被 `brand_pain_low` 单独卡在 `B_trimmed`。

## 代码修复

### 1. 关键词与 hybrid 收口

- `backend/app/services/analysis/analysis_query_support.py`
  - `apply_keyword_stopwords()` 改为始终合并默认停用词
  - 默认停用词新增 `product/products`
- `backend/app/services/analysis/analysis_engine.py`
  - 新增 `_filter_posts_for_open_topic_route()`
  - 在 `all_posts = _merge_posts_by_id(all_posts, hybrid_posts)` 之后立刻按 `open_topic_route` 做帖子层过滤

### 2. 证据纯度收口

- `backend/app/services/report/content_guardrails.py`
  - 低信号碎片新增：
    - `i analyzed`
    - `analyzed reddit`
    - `reddit discussions`
    - `reddit sentiment at scale`
- `backend/app/services/analysis/analysis_engine.py`
  - 新增 `_is_meta_analysis_post()`
  - `_build_source_examples()` 过滤交易帖和“分析 Reddit 数据”的元分析帖，不再让它们占证据位

### 3. 开放探索题品牌门禁收口

- `backend/app/services/facts_v2/quality.py`
  - `_should_relax_brand_requirement()` 扩展为识别“开放式探索题”
  - 只有满足以下条件时才放松品牌门槛：
    - 无明确品牌/竞品对比意图
    - 问题本身是“机会/切入/麻烦/痛点”型探索问题
    - `good_pains >= 2`
    - `solutions >= min_solutions_effective`
    - 品牌信号本身仍然稀薄
  - 这样避免把已经足够可读的 open question 误杀到 `B_trimmed`

## 测试结果

定向单测全部通过：

- `pytest tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_analysis_query_support.py tests/services/analysis/test_analysis_engine.py tests/services/report/test_content_guardrails.py -q`
- 结果：`98 passed`

新增/更新测试覆盖：

- `test_apply_keyword_stopwords_prefers_blacklist_contract`
- `test_build_source_examples_skips_meta_analysis_noise_posts`
- `test_filter_posts_for_open_topic_route_enforces_post_level_warzone_boundary`
- `test_is_low_signal_business_text_rejects_moderation_noise_fragments`
- `test_quality_gate_relaxes_brand_requirement_for_exploratory_open_question_even_with_comments`

## Live 验收结果

### EDC final live

- 输出文件：
  - `backend/reports/local-acceptance/open_question_live_final_1774600679.json`
- 结果：
  - `accepted = true`
  - `report_tier = A_full`
  - `issues = 0`

关键信号：

- 痛点标题已回到 EDC/收纳/携带语义：
  - `随身小物一多，口袋发鼓、分类混乱，拿取很不顺手`
  - `工具越带越多，但常用组合没有被整理好`
  - `出行和户外装备越带越乱`
- 目标社区已收敛在 EDC 战区：
  - `r/EDC`
  - `r/multitools`
  - `r/flashlight`
  - `r/knifeclub`
- Reddit 证据链接可点击且不再混入 `startups/entrepreneur` 垃圾样本

## 结论

这轮不是单题补丁，而是补了三层系统合同：

1. `open_topic_route` 从社区层下沉到帖子层
2. 关键词/混合检索不再带脏词扩散
3. 开放式探索题的质量门禁不再被无意义品牌要求误杀

现在已确认：

- `Family` live final 可出 `A_full`
- `EDC` live final 可出 `A_full`

说明主链已经开始具备跨题材稳定性，不再只是单题侥幸跑通。
