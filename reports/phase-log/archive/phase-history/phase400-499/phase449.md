# Phase 449 - 报告去系统化与业务价值转译第一轮落地

## 发现了什么？

- 用户给出的治理方案是对的，当前报告页问题不只是“文案不好看”，而是整条交付链还残留明显的系统自白：
  - 前端存在“怎么读、怎么工作的说明”
  - prompt 里还在放“系统/验证/口径”一类内部话
  - fallback 层仍把 `P/S`、健康度直接吐成机器判断
- 这类问题如果只改前端，会被下一轮 live 报告重新污染回来，必须前后端一起收。

## 是否需要修复？

- 需要，而且这轮已经先落地第一版治理。
- 目标不是“文案润色”，而是把报告重新收回“专家判断 -> 依据 -> 动作建议”的口径。

## 精确修复方法

### 1. 前端去备注化

- 更新标准报告页和真实报告页的硬编码文案：
  - 去掉“阅读顺序 / raw markdown / 分析过程”这类说明
  - 改成“市场切片 / 决策信号 / 市场诊断 / 机会收口”这类业务价值文案
- 更新完整报告正文组件顶部说明，去掉“共用同一套 1 到 7 结构”这类内部描述

### 2. Prompt 脱敏

- 更新 `backend/app/services/llm/report_prompts.py`
  - `REPORT_SYSTEM_PROMPT_V9`
  - `REPORT_SYSTEM_PROMPT_V9_JSON`
- 增加：
  - 资深跨境选品顾问人设
  - 禁语清单：`系统 / 前端 / 后端 / 逻辑 / 口径 / 验证 / 本轮分析` 等
  - 明确禁止 `估算口径`，统一改写成 `基于当前讨论强度判断`

### 3. 语义转译层

- 新增：
  - [semantic_translator.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/report/semantic_translator.py)
- 作用：
  - 把 `ps_ratio` 翻译成业务结论
  - 把 `health_assessment` 翻译成 `进场信号：...`
  - 把竞争度判断改成用户能直接理解的进场窗口语句

### 4. Fallback 去系统味

- 更新：
  - [structured_report_fallback.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/report/structured_report_fallback.py)
- 去掉：
  - `这是系统生成的统一结构报告`
  - `B/C 是 Full A 同骨架简化`
  - `先验证问题复现频率，再决定是否深挖`
- 改成：
  - 围绕核心抱怨、可切切口、进场信号、人群与收益的业务表达

## 验证

- `cd frontend && npm test -- src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/ReportPage.test.tsx`
  - `8 passed`
- `cd frontend && npm run build`
  - 通过
- `cd backend && pytest tests/services/llm/test_report_prompts_v9.py tests/services/report/test_structured_report_fallback.py -q`
  - `9 passed`
- `cd backend && python -m py_compile app/services/llm/report_prompts.py app/services/report/structured_report_fallback.py app/services/report/semantic_translator.py`
  - 通过

## 下一步系统性的计划是什么？

1. 继续扫真实报告页和标准报告页剩余的“系统味”硬编码。
2. 用新的 prompt 跑 1-2 条真实 live 报告，检查生成文案是否还残留“验证 / 口径 / 系统说明”。
3. 把语义转译层继续扩到更多指标和 blocked/scouting narrative。
4. 再刷新首页 6 张标准报告，做一轮人工文案抽检。

## 这次执行的价值是什么？

- 这轮把“去系统味”从建议变成了代码合同：
  - 前端不再教用户怎么读报告
  - prompt 不再鼓励模型说内部话
  - fallback 不再用机器判断直接怼用户
- 也就是说，报告开始更像一个懂业务的人在说话，而不是一个系统在解释自己。
