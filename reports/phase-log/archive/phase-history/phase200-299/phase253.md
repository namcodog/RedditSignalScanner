# Phase 253 - Round 3 深度审计（社区治理层 + 语义层）

执行时间: 2026-03-13

## 1. 发现了什么

- 这轮复核的重点，不是“会不会直接炸”，而是：
  - 社区治理链会不会在白名单、黑名单、评估、回填这些地方**静默放错源**
  - 语义链会不会在 DB 失败、YAML fallback、posts fallback 这些地方**静默降错级**
- 统一口径可以用一句大白话概括：
  - **Round 3 要解决的是“社区治理层和语义层会静默放错源、静默降错级”的问题。**
- 本轮重点看的链路：
  - `backend/app/services/community/community_pool_loader.py`
  - `backend/app/services/discovery/candidate_vetting_service.py`
  - `backend/app/services/discovery/evaluator_service.py`
  - `backend/app/services/community/community_discovery.py`
  - `backend/app/services/semantic/robust_loader.py`
  - `backend/app/services/semantic/candidate_extractor.py`
  - `backend/app/services/semantic/text_classifier.py`
  - `backend/app/tasks/semantic_task.py`
  - `backend/app/tasks/scoring_task.py`

## 2. 是否需要修复

- 需要。
- 核心原因有 3 类：
  - 社区池导入和候选社区回填，允许继续跑，但没有把“这次是完整导入还是降级导入”说清楚。
  - 语义加载和候选词提取，允许 fallback，但没有把“数据到底来自 DB、YAML 还是 posts fallback”说清楚。
  - 任务层返回值太模糊，外面很难区分这次是完整成功、降级成功，还是实际失败。

## 3. 精确修复方法

### 3.1 社区治理链

- `community_pool_loader.py`
  - 强制白名单模式下改成 fail-closed。
  - 旧 Top1000 噪音源不再允许回流社区池；即使文件存在，也只能显式标记 `deprecated_ignored`，不能参与导入。
- `candidate_vetting_service.py`
  - 被社区池黑名单拦截、没有回填目标、评估触发失败等场景，要留下结构化状态，而不是只剩空结果。
- `evaluator_service.py`
  - DB 样本与 API 样本要明确区分，审批结果要能看出是真评估，还是 DB 样本不够后退 API 的结果。
- `community_discovery.py`
  - 关键词搜索失败不能只 `continue`，要留 warning 和上下文。

### 3.2 语义 fallback 合同

- `robust_loader.py`
  - 修正 `.yml` fallback 不能再用 JSON 读的问题。
  - 统一返回 `db / yaml / yaml_fallback / load_failed / empty_fallback` 这类来源状态。
- `candidate_extractor.py`
  - 修正 DB 提取路径的时间窗参数和 fallback 合同。
  - 候选词来源要明确区分 `comments_db` 和 `posts_fallback`。
- `text_classifier.py`
  - 去掉关键路径里的 `print(...)`，统一换成结构化日志。

### 3.3 任务状态协议

- `semantic_task.py`
  - 统一返回 `completed / degraded / failed`。
  - 把提取来源、fallback 状态一起带回结果包。
- `scoring_task.py`
  - 默认补分继续保留，但必须显式标记 `score_source=rulebook_v1_default_fill`。

## 4. 下一步系统性的计划

- 先补测试，再落实现。
- 执行顺序固定为：
  1. 社区治理链 fail-closed + 状态协议
  2. 语义 fallback 来源合同
  3. 任务层 `status/source/fallback` 协议
  4. 跑组合回归并把口径写回总计划文档

## 5. 这次执行的价值

- 这轮审计把 Round 3 的问题从“看起来有很多 best-effort”收敛成了 1 条清楚主线：
  - **允许降级，但绝不允许静默降级。**
- 也就是把社区治理层和语义层重新拉回我们想要的工程方式：
  - 各模块职责清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路顺畅可控
