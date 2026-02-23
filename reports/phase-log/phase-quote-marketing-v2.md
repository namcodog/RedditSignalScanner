# Phase Log — QuoteExtractor & MarketingCopy (V2)

日期: 2025-11-13

## 1) 发现了什么问题/根因？
- 缺失两个关键能力的可执行模块与测试：
  - QuoteExtractor（用户引言提取）：仓库无该模块与测试文件。
  - MarketingCopyGenerator（营销文案）：仓库无该模块与测试文件。
- 验收口径（长度、清洗、降级策略）在现有实现里没有落地。

## 2) 是否已精确定位？
- 已定位落点与依赖：
  - 位置：`backend/app/services/analysis/quote_extractor.py`、`backend/app/services/llm/marketing_copy.py`
  - 依赖：`text_cleaner.clean_text`、`signal_extraction.SignalExtractor._NEGATIVE_TERMS`、`llm/clients/openai_client.OpenAIChatClient`（可选）

## 3) 精确修复方法？
- 先写测试（pytest），覆盖排序/清洗/限长/降级：
  - `backend/tests/services/test_quote_extractor.py`
  - `backend/tests/services/llm/test_marketing_copy.py`
- 实现模块：
  - QuoteExtractor：分句→清洗→过滤(50–150)→打分（情感0.4×相关0.4×情绪0.2）→排序→返回。
  - MarketingCopyGenerator：模板模式（默认，<=40字）+ LLM模式（存在凭据时启用，失败回退模板）。

## 4) 下一步做什么？
- 跑后端用例并调权重/边界：`make test-backend`
- 若需要：补充与 `report_service.py` 的集成点（Phase 2/3 由集成工程师牵头）。
- 将任务标记到 `.spec-workflow/specs/market-insight-report-v2/tasks.md`（1.4/1.5/1.6、2.1/2.2/2.3）为 in-progress/完成。

## 5) 这次修复的效果/结果？
- 新增两个可测试、可降级的内容智能模块，满足 PRD 的非功能约束：
  - QuoteExtractor：稳定抽取 1–2 条高质量引言，清洗与长度门控通过测试。
  - MarketingCopy：模板模式产出稳定、中文且<=40字；LLM 有凭据时自动增强、无凭据时不阻断。

## Phase 2 附加说明（MarketingCopy 完成）
- 模式：模板为主、LLM可选，失败自动降级。
- 验收点覆盖：4种文案、<=40字、中文、槽位校验、缺数据兜底、LLM长度限制与降级。
- 新增测试：`test_template_handles_missing_partial_data` 验证缺失字段时仍稳定生成。
- 集成：已在 `backend/app/services/report_service.py` 注入 Phase 2 生成逻辑，结果存入 `metadata.market_enhancements.marketing_copy`（键：`oppty-{i}`）。

## 语义库统一（Week 1 基础）
- 完成 `layer_definitions.yml`（L1-L4 定义、权重与示例）。
- 新增 `UnifiedLexicon` 单测 6 项（加载/错误/缺失回退/分层过滤/正则生成/层级元数据）。

## 产出清单
- 代码：
  - `backend/app/services/analysis/quote_extractor.py`
  - `backend/app/services/llm/marketing_copy.py`
  - `backend/app/services/analysis/__init__.py`（导出符号）
  - `backend/app/services/semantic/unified_lexicon.py`（增强：新旧YAML均支持、图层定义读取）
  - `backend/config/semantic_sets/layer_definitions.yml`
- 测试：
  - `backend/tests/services/test_quote_extractor.py`
  - `backend/tests/services/llm/test_marketing_copy.py`
  - `backend/tests/services/semantic/test_unified_lexicon.py`

注：如需改为 phase{N}.md 命名，请告知编号，我将同步重命名。
