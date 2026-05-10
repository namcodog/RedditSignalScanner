# Phase 460 - Evidence Selection 第一段抽离

## 背景

在完成 `Worker / State Orchestration` 的隔离 runtime 合同之后，这一轮开始进入中段重构的下一段：`Evidence Selection`。

问题已经很明确：

- `analysis_engine.py` 里的 `_apply_query_focus_filter()` 继续扩下去，只会变成更大的领域硬编码集合。
- `analysis_payload_loader.py` 和 `structured_report_fallback.py` 也不应该再承担“补选证据”的正向职责。

所以这轮的目标，不是继续补规则，而是把“证据选择”正式抽成独立模块。

## 本轮改动

### 1. 新增通用证据选择模块

- 文件：`backend/app/services/analysis/evidence_selection.py`

做的事情：

- 定义统一输入：
  - `product_description`
  - `keywords`
  - `route_reasons`
  - `preferred_communities`
- 统一根据这些输入对帖子做打分和过滤
- 保留 fallback，但不再继续把某个题材的 if/else 堆进 `analysis_engine.py`

### 2. 将旧入口改为调用新模块

- 文件：`backend/app/services/analysis/analysis_engine.py`

现在 `_apply_query_focus_filter()` 不再自己维护那套越来越长的领域 focus 规则，而是转调 `select_evidence_posts(...)`。

这意味着：

- `analysis_engine.py` 开始回到“主流程编排”职责
- `evidence_selection.py` 开始承接“选证据”职责

### 3. 补跨题材测试

- 文件：`backend/tests/services/analysis/test_evidence_selection.py`

覆盖：

- PayPal
- Family
- Coffee
- 无命中回退

### 4. 补旧入口回归测试

- 文件：`backend/tests/services/analysis/test_analysis_engine.py`

确认旧入口仍然能正确接到新模块，不会因为抽层把主链接断。

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_evidence_selection.py -q`
- `cd backend && pytest tests/services/analysis/test_analysis_engine.py -q -k 'query_focus or open_topic_route'`
- `cd backend && python -m py_compile app/services/analysis/evidence_selection.py app/services/analysis/analysis_engine.py`

## 发现

- 证据选择这层一旦抽出来，之前很多“领域硬编码是不是越来越多”的问题就能被直接看见。
- 单个宽词命中不能直接算“有效证据命中”，否则像 `newborn` 这种词会把宽帖也拉进来。
- 真正通用的证据选择，必须把：
  - 宽词
  - 具体场景词
  - 社区优先级
  - 题目上下文
  一起纳入同一套打分合同。

## 结论

这轮还没有完成 `Evidence Ledger`，但已经完成了非常关键的第一刀：

- 证据选择开始脱离 `analysis_engine.py` 这类 God Object
- 也开始脱离 payload loader / fallback 的补洞逻辑

也就是说：

- 中段重构不再只停留在评估
- 现在已经实装到第二段了

## 下一步

- 继续推进 `Evidence Ledger`
- 目标是让 report 层后续只读取已经选好的证据面，而不是继续自己拼 `facts_slice / sample_posts_db / user_examples`
