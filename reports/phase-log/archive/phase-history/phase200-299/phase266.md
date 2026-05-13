# Phase 266 - Round 4 第三阶段深修（hotpost / 爆帖速递）

## 目的
- 完成 Round 4 最后一段深修，把爆帖速递这条链路里最容易“表面成功、实际降级”的地方收干净：
  - 中文 query 翻译失败后静默 fallback
  - summary 失败后静默 fallback
  - report_llm 失败后静默 `None`
  - 最终返回仍统一写成 `status=success`
- 顺手把 hotpost 的状态/来源协议补齐，让人和 AI 都能一眼看出这次结果来自哪里

## 这轮修了什么

### 1. query resolver 开始说真话
- `backend/app/services/hotpost/query_resolver.py`
  - `HotpostQueryResolution` 新增 `degraded_reason`
  - 以前：
    - LLM 翻译失败 -> 静默回退原 query
    - 坏 JSON -> 静默 fallback
  - 现在：
    - `llm_client_unavailable`
    - `llm_generate_failed`
    - `llm_response_invalid`
  - 这些原因都会显式带出来

### 2. summary 不再只回一段字符串
- `backend/app/services/hotpost/service.py`
- 新增：
  - `backend/app/services/hotpost/result_meta.py`
- `_maybe_llm_summary()` 以前只返回 summary 文本
- 现在返回结构化结果：
  - `text`
  - `source` (`llm` / `fallback`)
  - `degraded_reason`
- 当前会明确区分：
  - `low_confidence`
  - `missing_api_key`
  - `llm_generate_failed`
  - `llm_empty_output`

### 3. report_llm 不再把失败吞成 None
- `backend/app/services/hotpost/report_llm.py`
- `generate_hotpost_llm_report()` 现在返回：
  - `report`
  - `source` (`llm` / `fallback` / `disabled`)
  - `degraded_reason`
- 以前：
  - 调用失败 -> 异常在 service 里被吞
  - JSON 坏掉 -> 直接 `None`
- 现在：
  - `llm_generate_failed`
  - `invalid_json`
  - 都会明确记录

### 4. hotpost 最终响应不再混着说
- `backend/app/services/hotpost/service.py`
  - 缓存命中时：
    - 旧 `success` 会规范成 `completed`
    - `debug_info.response_source = "cache"`
  - 实时搜索时：
    - 顶层 `status` 现在按真实情况给：
      - `completed`
      - `degraded`
    - `debug_info` 新增：
      - `query_source`
      - `query_degraded_reason`
      - `summary_source`
      - `summary_degraded_reason`
      - `report_source`
      - `report_degraded_reason`
      - `llm_report_applied`
      - `degraded_reasons`
      - `response_source`
  - live 搜索结束后会补 `queue_tracker.mark_completed()`，不再只在 cache hit 时标完成

### 5. SSE 和前端类型一起收口
- `backend/app/api/v1/endpoints/hotpost.py`
  - SSE 现在把 `success` / `degraded` / `completed` 都当完成事件处理
- `frontend/src/types/hotpost.ts`
  - `status` 增加 `degraded`
  - `debug_info` 同步补齐来源/降级字段
  - 顺手修掉文件里一个已有的重复字段 `mentions`，不然 `npm run build` 会直接失败

## 这轮的深层修正点
- hotpost 现在开始说真话了：
  - 实时结果就是实时结果
  - 缓存结果就是缓存结果
  - fallback 会带原因
  - report_llm 没产出，不再伪装成“只是没这块内容”
- 这次没有改数据库 schema，也没有新增 migration

## 测试

### 定向回归
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_report_llm.py tests/services/hotpost/test_hotpost_summary.py tests/api/test_hotpost.py -q`
- 结果：`11 passed`

### hotpost 全量服务回归
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost -q`
- 结果：`45 passed`

### 质量门禁
- `SKIP_DB_RESET=1 make test-quality-gate`
- 结果：`27 passed`

### 前端构建
- `cd frontend && npm run build`
- 结果：通过
- 过程中暴露出 `frontend/src/types/hotpost.ts` 里一个旧的重复字段 `mentions`，这轮顺手清掉了

## 当前统一口径
- hotpost 就是“爆帖速递模块”
- 这条链现在统一按这套话说：
  - `completed`：结果完整返回，且没有结构化降级原因
  - `degraded`：结果返回了，但 query / summary / report 至少有一段走了 fallback 或降级
  - `failed`：结果没跑成（这轮没有改主异常出口，只收口了已完成返回时的语义）
- 结果来源统一看：
  - `from_cache`
  - `debug_info.response_source`
  - `debug_info.query_source`
  - `debug_info.summary_source`
  - `debug_info.report_source`

## 结论
- Round 4 第三阶段（hotpost / 爆帖速递）已完成
- 当前 Round 4 状态应定义为：
  - `phase263`：已审计
  - `phase264`：第一阶段（监控/基础设施）已完成
  - `phase265`：第二阶段（LLM）已完成
  - `phase266`：第三阶段（hotpost）已完成
- 至此，Round 4 可以正式收尾，下一步进入 Round 5
