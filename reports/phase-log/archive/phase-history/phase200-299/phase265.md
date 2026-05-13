# Phase 265 - Round 4 第二阶段深修（LLM 链路）

## 目的
- 继续推进 Round 4，先把 LLM 链路里最危险的两件事收掉：
  - Provider 真失败却被压成空字符串
  - 标签任务中间失败很多，最后还返回 `status=ok`
- 同时顺手做文件瘦身，降低 AI 和人阅读成本

## 这轮修了什么

### 1. LLM 客户端开始说真话
- `backend/app/services/llm/interfaces.py`
  - 新增 `LLMClientError`
- `backend/app/services/llm/clients/openai_client.py`
  - 以前：SDK/HTTP 失败会 `print` 然后返回空字符串
  - 现在：改成结构化日志 + 抛 `LLMClientError`
- `backend/app/services/llm/clients/gemini_client.py`
  - 以前：HTTP 失败、缺 key、连接异常都会返回空字符串
  - 现在：统一抛 `LLMClientError`

### 2. 标签任务不再“中间失败很多，最后还是 ok”
- `backend/app/tasks/llm_label_task.py`
  - 以前：批量标签里大量 `except rollback continue`，最后不管中间失败多少，几乎都只回 `status=ok`
  - 现在：统一返回更清楚的状态和计数：
    - `completed`
    - `degraded`
    - `failed`
    - `missing_api_key`
    - `no_candidates`
  - 同时返回：
    - `attempted`
    - `fallback_batches`
    - `llm_failures`
    - `persist_failures`
    - `degraded_reasons`
- `backfill_legacy_labels`
  - 以前：同步/持久化失败也会被吞，最后还是 `ok`
  - 现在：也会区分 `completed / degraded / failed`

### 3. 把重复批处理逻辑外提，主文件变短
- 新增：
  - `backend/app/tasks/llm_label_support.py`
- 这次把批处理、fallback、savepoint 持久化、状态统计都抽进 support
- 结果：
  - `llm_label_task.py` 从 **1014 行降到 988 行**
  - 批处理逻辑不再重复四遍

### 4. LLMLabeler 自己也补了可观测性
- `backend/app/services/llm/labeling.py`
  - 以前：batch 解析失败只返回 `[]`
  - 现在：会留 warning，明确这是“空/不可解析 batch 响应”

## 这轮的深层修正点
- 标签任务现在用 nested transaction / savepoint 处理单项持久化
- 以前一个 item 落库失败可能把同批前面成功的也一起回滚，还把 `processed` 算进去
- 现在：
  - 单项失败只影响自己
  - commit 失败也会明确计入 `persist_failures`
  - 返回值更接近真实落库结果

## 测试

### 定向测试
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/llm/test_llm_clients.py tests/services/labeling/test_llm_labeler.py tests/tasks/test_llm_label_task.py -q`
- 结果：`9 passed`

### 相关回归
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/llm/test_marketing_copy.py -q`
- 结果：通过

### 质量门禁
- `SKIP_DB_RESET=1 make test-quality-gate`
- 结果：`27 passed`

## 额外发现（未在本轮修）
- 我加跑了这组更宽的安全回归：
  - `tests/services/report/test_report_service_market_mode.py`
  - `tests/services/analysis/test_t1_market_agent_llm.py`
- 其中 3 条失败，但都不是这轮改动文件直接引起的：
  - `test_report_service_market_mode_uses_market_template`
    - 断言的是模板 HTML 内容，但当前返回的是 `<html>demo</html>`
  - `test_t1_market_agent_llm.py` 两条
    - 当前 `CommunityStat` 构造参数和测试夹具不匹配
- 这轮没有改这些服务文件，所以这里只记账，不混进本轮修复成果里

## 当前统一口径
- LLM 客户端现在开始说真话了：
  - 真返回空文本：空文本
  - 真请求失败：`LLMClientError`
- 标签任务现在也开始说真话了：
  - `completed`：这次批任务完整跑成
  - `degraded`：跑成了，但中间走了 fallback 或有部分失败
  - `failed`：这次基本没跑成

## 结论
- Round 4 第二阶段（LLM 链路）已完成
- 当前 Round 4 状态应定义为：
  - `phase263`：已审计
  - `phase264`：第一阶段（监控/基础设施）已完成
  - `phase265`：第二阶段（LLM）已完成
  - 下一步只剩第三阶段：`hotpost`
