# Phase 223

## 目标
- 按 SOP 落地核心能力：关键词预检拆分、LLM 输出过滤、友好错误、调试信息输出、社区策略优化与后置过滤。

## 完成内容
- 关键词预检拆分：超过 50 字符自动拆分为多次查询并合并去重，支持 OR 语法分段。
- Opportunity 后置过滤：启用简单相关性过滤（基于关键词匹配），并记录过滤数量。
- 智能社区策略：Opportunity 默认不限社区；非 Opportunity 自动推荐 5 个社区。
- 调试信息输出：新增 debug_info（实际关键词/社区/时间范围/过滤量等）与 notes 提示；Markdown 报告增加调试信息段落。
- LLM 输出过滤 + 日志：新增 sanitize_llm_report，过滤多余字段并记录日志，避免 Schema 阻塞。
- 友好错误包装：捕获 ValidationError 并返回可读错误。
- 前端类型对齐：补充 notes/debug_info 与证据字段。

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_query_split.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_llm_sanitize.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_rules.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_enrichment.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_summary.py -q`
- `pytest backend/tests/services/llm/test_openai_client.py -q`

## 结论
- Phase 223 完成，SOP 核心落地项已实现并通过测试。
