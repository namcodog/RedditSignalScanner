# Phase 437 - Prompt 压缩与歧义清理

## 本轮目标

优化完整报告与结构化报告的 prompt：

- 能简洁的地方尽量简洁
- 去掉旧口径和歧义表达
- 保持“通俗易懂”的输出要求

## 发现了什么

1. 现有 `v9` prompt 明显偏长：
   - narrative 总长度约 `2340`
   - structured 总长度约 `3191`
2. prompt 里仍残留旧世界字段口径，如 `trend_summary / market_saturation`，而当前主链已经是：
   - `canonical_report_json + facts_slice`
3. 这些旧字段提示会制造歧义：
   - 模型会在“按当前 canonical 合同写”与“按旧字段名映射写”之间摇摆。

## 是否需要修复

需要。

这不是纯 token 优化，而是合同清理。prompt 不收干净，后面报告风格和结构都容易继续漂。

## 精确修复方法

- 更新 [`backend/app/services/llm/report_prompts.py`](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/llm/report_prompts.py)
  - `REPORT_SYSTEM_PROMPT_V9` 改为短版硬规则：
    - 只基于 facts
    - 优先依据 `canonical_report_json`
    - `facts_slice` 只做补证据
    - 全文通俗、人话、可行动
  - `build_complete_report_v9()`：
    - 压缩结构说明
    - 去掉重复约束
    - 统一成更直白的章节要求
  - `REPORT_SYSTEM_PROMPT_V9_JSON`：
    - 删除旧字段映射
    - 强化“结构化 JSON + 通俗补全 + 同源合同”
  - `build_report_structured_prompt_v9()`：
    - 保留 JSON 骨架
    - 收短写作要求，避免重复描述

## 验证结果

- prompt 长度变化：
  - narrative：`2340 -> 1020`
  - structured：`3191 -> 2323`
- 测试：
  - `pytest tests/services/llm/test_report_prompts_v9.py tests/services/report/test_narrative_report_workflow.py tests/services/report/test_report_assembly_deps_factory.py tests/services/report/test_report_assembly_workflow.py -q`
  - `13 passed`

## 补充测试

- 更新 [`backend/tests/services/llm/test_report_prompts_v9.py`](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/llm/test_report_prompts_v9.py)
  - 锁定 `canonical_report_json` 为 prompt 优先语义
  - 增加 prompt 体积上限回归测试，防止后续继续膨胀

## 当前结果

这轮之后，prompt 更短、更直白，也更贴合当前系统合同。
后续如果还要继续提升报告质量，应该优先调“表达强度”和“样本选择”，而不是再把 prompt 写长。
