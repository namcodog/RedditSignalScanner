# Phase 251 - Round 2 深层修复落地（分析结果拆层 / 降级链显式化 / 配置语义可观测）

执行时间: 2026-03-13

## 1. 发现了什么

- Round 2 真正要修的不是“算法细节还不够准”，而是 3 条会把加工链路口径弄歪的深层问题：
  - `analysis_task.py`：真实分析结果和展示兜底卡片混层，甚至会补伪链接、补自动证据。
  - `pain_cluster.py` → `facts_v2/midstream.py` → `facts_v2/quality.py`：上游失败会一路伪装成 `pains_low / brand_pain_low`。
  - `topic_profiles.py` / `t1_stats.py` / `facts_v2/midstream.py`：配置失败、embedding 失败、domain pain 配置失败时大多静默回退。
- 这三块本质上都是“模块各自能继续跑，但说的话已经不是一回事”：
  - 分析层本来应该负责**只产出真实分析结果**；
  - facts 层本来应该负责**把降级事实明确写出来**；
  - 配置/语义层本来应该负责**失败可观测，而不是偷偷退默认值继续跑**。
- 参考异步持久化、降级链设计和观测性实践后，确认这轮最稳的方向是：
  - 真实结果和展示兜底拆层；
  - 降级状态结构化透传；
  - 保持兼容旧测试替身，不把 monkeypatch/mock 一起打崩。

## 2. 是否需要修复

- 需要，已经落地。
- 这轮不是补几个 warning，而是把数据加工层重新收成 3 层说真话的协议：
  - `analysis_task.py`：只落真实 insight，不再让展示兜底冒充正式证据。
  - `pain_cluster.py` / `midstream.py` / `quality.py`：降级链显式写入 diagnostics 和 quality flags。
  - `topic_profiles.py` / `t1_stats.py` / `midstream.py`：配置层、语义层、domain pain 层的回退统一留下结构化状态。

## 3. 精确修复方法

### 3.1 `backend/app/tasks/analysis_task.py`

- 最小 facts 包 `_build_minimal_facts_package(...)` 现在会显式带上：
  - `facts_v2_package_status="missing_generated_minimal"`
  - `fallback_generated=true`
- 新增真实证据收口 helper：
  - `_load_phrase_mapping`
  - `_normalize_insight_text`
  - `_coerce_evidence_timestamp`
  - `_collect_real_evidence_posts`
  - `_persist_insight_cards`
- `_persist_insight_cards(...)` 现在只会持久化真实分析结果：
  - 先清掉旧 `InsightCard(kind="insight")`
  - 只吃 `opportunities` / `pain_points`
  - 没有真实 `url/permalink` + 摘录的 evidence 不再入库
  - 不再用 `task.id` 拼伪 Reddit 链接
  - 不再把 `action_items` 这种展示兜底内容当正式 insight 落库
- insight 持久化失败仍然不拖垮主流程，但现在会打明确 warning 和堆栈，不再悄悄吞掉。

### 3.2 `backend/app/services/analysis/pain_cluster.py`

- `cluster_pain_points_auto(...)` 增加可选 `diagnostics` 参数。
- 现在会把关键状态显式写出来：
  - `db_labels`
  - `db_error`
  - `db_error_tfidf_fallback`
  - `tfidf_fallback`
  - `fallback_error`
  - `empty`
- 失败时改成 warning + diagnostics，而不是直接空列表糊过去。

### 3.3 `backend/app/services/facts_v2/midstream.py` + `backend/app/services/facts_v2/quality.py`

- `compute_pain_clusters_v2(...)` 和 `compute_brand_pain_v2(...)` 都增加可选 `diagnostics`。
- 现在会显式记录：
  - `pain_clusters_pipeline_status`
  - `brand_pain_pipeline_status`
  - `domain_pain_config_status`
  - 以及对应 error 字段
- `quality_check_facts_v2(...)` 会把这些 diagnostics 打进 metrics 和 flags：
  - `topic_profiles_degraded`
  - `semantic_search_degraded`
  - `domain_pain_config_degraded`
  - `pains_pipeline_degraded`
  - `brand_pain_pipeline_degraded`
- 这样质量门不再只会说“你 pain 太少了”，而是能说清楚“是样本薄，还是链路中途降级了”。

### 3.4 `backend/app/services/analysis/topic_profiles.py` + `backend/app/services/analysis/t1_stats.py`

- 配置和语义相关入口都加了 diagnostics 透传：
  - `load_topic_profiles(...)`
  - `load_brand_discovery_defaults(...)`
  - `fetch_topic_relevant_communities(...)`
- 现在会明确留下：
  - `topic_profiles_status`
  - `semantic_search_status`
  - 对应错误信息
- `print(...)` 级别的临时提示，改成了结构化 warning，更适合后续统一排查。

### 3.5 `backend/app/services/analysis/analysis_engine.py`

- 在 `run_analysis(...)` 里引入统一 `facts_diagnostics`。
- Topic profile、community relevance、pain cluster 这些链路的降级信息，都会透传进：
  - `facts_v2_package["diagnostics"]`
  - `sources["analysis_diagnostics"]`
- 为了不把老测试替身打坏，新增调用都做了兼容：
  - 如果 monkeypatch 的函数不接受 `diagnostics=`，会自动回退到旧签名。

### 3.6 测试层一起收口

- `test_pain_cluster_auto.py`
  - 新增降级状态和完全失败场景测试
- `test_facts_v2_midstream.py`
  - 新增 no-domain-mapping / blocked-by-empty-pain-clusters 测试
- `test_facts_v2_quality_gate.py`
  - 新增 diagnostics → degraded flags 测试
- `test_topic_profiles.py`
  - 新增 YAML 非法时 diagnostics 记录测试
- `test_t1_stats_determinism.py`
  - 补 semantic fallback diagnostics 断言
- `test_facts_snapshots.py`
  - 补真实 insight 证据持久化测试
  - 补清理旧卡片、跳过 synthetic entry 测试

## 4. 验证结果

- `python -m py_compile`（本轮改动代码 + 测试）
  - 通过
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/analysis/test_pain_cluster_auto.py tests/services/analysis/test_facts_v2_midstream.py tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_topic_profiles.py tests/services/analysis/test_t1_stats_determinism.py -q`
  - `46 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/tasks/test_facts_snapshots.py -q`
  - `9 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py tests/services/analysis/test_analysis_engine_topic_profile_filters.py -q`
  - `5 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/core/test_task_system.py tests/tasks/test_facts_snapshots.py tests/services/analysis/test_pain_cluster_auto.py tests/services/analysis/test_facts_v2_midstream.py tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_topic_profiles.py tests/services/analysis/test_t1_stats_determinism.py tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py tests/services/analysis/test_analysis_engine_topic_profile_filters.py -q`
  - `67 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

说明：
- `pytest.ini` 里仍有仓库现成警告：`Unknown config option: asyncio_default_fixture_loop_scope`
- 这不是本轮引入的问题。

## 5. 这次执行的价值

- 这轮把 Round 2 从“找到了哪里会悄悄变味”推进到了“链路已经开始说真话”的状态。
- 更重要的是，加工链路的职责边界被重新收清楚了：
  - 分析层只负责真实分析结果，不再拿展示兜底冒充正式证据；
  - facts 层只负责把中间结果和降级状态清楚表达出来，不再把上游失败伪装成数据薄；
  - 配置/语义层允许回退，但所有回退都要留痕，调用方必须知道自己拿到的是完整结果还是降级结果。
- 这更接近我们要的工程目标：
  - 各模块职责清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路顺畅可控
