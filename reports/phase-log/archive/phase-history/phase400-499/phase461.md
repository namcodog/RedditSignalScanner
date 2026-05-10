# Phase 461 - Evidence Ledger 第一段落地

## 背景

在完成：

- `Worker / State Orchestration`
- `Evidence Selection`

之后，下一步必须解决的是：

- report 层现在还是有很多入口在自己拼证据
- `example_posts / user_examples / sample_posts_db / source_examples`
  这些来源散落在不同层里

所以这轮的目标，是先把统一证据账本接进主链。

## 本轮改动

### 1. 新增统一证据账本模块

- 文件：`backend/app/services/analysis/evidence_ledger.py`

职责：

- 统一构建 pain 证据链
- 统一构建 opportunity 证据链
- 提供账本查询接口

账本输入来源：

- `example_posts`
- `source_examples`
- `sample_comments_db`
- `sample_posts_db`
- `user_examples`

### 2. 在 analysis 主链产出账本

- 文件：`backend/app/services/analysis/analysis_engine.py`

现在 analysis 主链在产出 `facts_v2_package / facts_slice` 之前，会先构建 `evidence_ledger`。

### 3. 将账本写入 report 可消费层

- 文件：`backend/app/services/facts_v2/slice.py`

现在 `facts_slice` 会带出 `evidence_ledger`，report 层可以统一读取。

### 4. 让 fallback 优先读账本

- 文件：`backend/app/services/report/structured_report_fallback.py`

当前 pain / opportunity 的 `evidence_chain` 已经开始优先读取 `evidence_ledger`。

也就是说：

- fallback 不再只是自己临时拼证据
- 开始转成“优先读 analysis 层已经准备好的账本”

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_evidence_ledger.py -q`
- `cd backend && pytest tests/services/report/test_structured_report_fallback.py -q`
- `cd backend && python -m py_compile app/services/analysis/evidence_ledger.py app/services/analysis/analysis_engine.py app/services/facts_v2/slice.py app/services/report/structured_report_fallback.py`

## 结论

这轮还没有把整个 report 层全部切完，但已经形成了第一段闭环：

- analysis 层产账本
- facts_slice 带账本
- fallback 读账本

这说明“统一证据读取面”已经开始落地，不再只是设计口号。

## 下一步

- 继续把：
  - `report_payload_builder`
  - `opportunity_report`
  - `controlled_generator`
  等更多 report 入口往 `evidence_ledger` 收。
