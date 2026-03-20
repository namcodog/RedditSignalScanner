# Phase 254 - Round 3 深层修复落地（社区治理说真话 / 语义 fallback 留痕 / 任务状态明确）

执行时间: 2026-03-13

## 1. 发现了什么

- Round 3 不是“多补几个 warning”这么简单，真正的问题是：
  - 社区治理链会在白名单、黑名单、评估触发这些地方继续跑，但外面看不出它已经降级。
  - 语义链会在 DB 失败后退 YAML、退 posts fallback，但没有把来源说清楚。
  - 任务层会继续回一个“看起来成功”的字典，外面很难判断这次到底是成功、降级还是失败。

## 2. 是否需要修复

- 需要，已经落地。
- 统一后的口径是：
  - 社区治理层允许 best-effort，但不能静默放行。
  - 语义层允许 fallback，但必须说清楚来源和原因。
  - 任务层允许返回结构化结果，但状态必须说真话。

## 3. 精确修复方法

### 3.1 社区治理链

- `backend/app/services/community/community_pool_loader.py`
  - 强制白名单模式下，配置坏了直接 fail-closed。
  - 旧 Top1000 文件现在只会显式标记 `deprecated_ignored`，不会再参与社区池导入，更不会把噪音社区拉回数据表。
- `backend/app/services/discovery/candidate_vetting_service.py`
  - 黑名单拦截、无回填目标、评估触发失败，现在都会写进 `metrics.vetting`。
  - 评估任务投递成功/失败会明确写成 `queued / failed`。
- `backend/app/services/discovery/evaluator_service.py`
  - DB 样本与 API fallback 现在会显式留下：
    - `sample_source`
    - `sample_fetch_status`
- `backend/app/services/community/community_discovery.py`
  - 搜索失败不再静默 `continue`，会打 warning。

### 3.2 语义 fallback 合同

- `backend/app/services/semantic/robust_loader.py`
  - `.yml/.yaml` 现在真的用 `yaml.safe_load`。
  - metrics 新增：
    - `source_status`
    - `last_error`
  - DB 失败后退 YAML，会显式标记 `yaml_fallback`。
- `backend/app/services/semantic/candidate_extractor.py`
  - DB 候选词提取现在使用 Python 先算好的 cutoff，不再靠有问题的文本 interval。
  - diagnostics 会留下：
    - `candidate_extract_source`
    - `candidate_extract_status`
    - `candidate_extract_error`
  - comments 路径记为 `comments_db`，fallback 路径记为 `posts_fallback`。
- `backend/app/services/semantic/text_classifier.py`
  - 关键路径的临时 `print(...)` 改成了 logger。

### 3.3 任务状态协议

- `backend/app/tasks/semantic_task.py`
  - 提取、同步、打标任务现在统一返回 `status`。
  - 候选词提取结果会一起带上 `extraction_source` / `extraction_status`。
  - 出错不再返回模糊包，统一收成 `failed`。
- `backend/app/tasks/scoring_task.py`
  - 评分兜底结果统一显式标记：
    - `status`
    - `score_source=rulebook_v1_default_fill`

### 3.4 测试一起锁住

- 新增/更新测试：
  - `backend/tests/services/community/test_community_pool_loader.py`
  - `backend/tests/services/community/test_candidate_vetting_service.py`
  - `backend/tests/services/community/test_community_pool_loader_full.py`
  - `backend/tests/services/semantic/test_robust_semantic_loader.py`
  - `backend/tests/services/semantic/test_candidate_extractor.py`
  - `backend/tests/tasks/test_semantic_task.py`
  - `backend/tests/tasks/test_scoring_task.py`

## 4. 验证结果

- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_pool_loader.py tests/services/community/test_candidate_vetting_service.py tests/services/semantic/test_robust_semantic_loader.py tests/services/semantic/test_candidate_extractor.py tests/tasks/test_semantic_task.py tests/tasks/test_scoring_task.py -q`
  - `19 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_pool_loader_full.py tests/services/community/test_community_discovery.py tests/services/community/test_community_discovery_service.py tests/services/community/test_evaluator_service.py tests/services/semantic/test_robust_semantic_loader.py tests/services/semantic/test_candidate_extractor.py tests/services/semantic/test_semantic_scorer.py tests/services/semantic/test_semantic_scorer_legacy.py tests/services/semantic/test_text_classifier.py tests/tasks/test_semantic_task.py tests/tasks/test_scoring_task.py -q`
  - `32 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`
- `make check-determinism`
  - 通过

说明：
- 启动测试时仍会看到第三方依赖的 `pkg_resources is deprecated` warning。
- 这不是本轮引入的问题。

## 5. 这次执行的价值

- 这轮把 Round 3 从“发现社区治理和语义层会静默降级”推进到了“降级已被结构化表达并被测试锁住”。
- 现在系统更接近我们要的状态：
  - 社区治理层不会再悄悄放错源
  - 语义层不会再悄悄换来源
  - 任务层不会再拿模糊成功包糊弄下游
- 用大白话说，就是：
  - **以前它会继续跑，但不告诉你自己已经变味了；现在它继续跑也会老老实实告诉你这次到底是完整结果、降级结果，还是失败。**
