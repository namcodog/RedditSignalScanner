# Phase 756 - Signal Prompt Tone And Gemini JSON Guard

## 判断

潜力快帖的主要问题不是前端结构，而是两层叠加：

- signal prompt 为了“像人说话”容易诱导 Gemini 写出过度情绪词。
- semantic readout 后处理会把自然的 `continue_signal` 继续拼接低质量英文锚点，拉低读感。

## 改动

- 收紧 `signal_compact_prompt.md`：强调“先把意思讲准，再讲顺”，禁止靠“破防、亏死了、忍到极限、万能药、幻想”等词硬顶。
- `signal max_tokens` 保持 2200：2000 在实测里仍出现 Gemini 3 JSON 截断，2200 是当前结构化输出安全上限，不代表每张都会消耗 2200。
- `_generate_json` 增加一次结构化重试：第一次 JSON 不合法时，按同一输入重试合法 JSON object，不生成兜底内容。
- `semantic_readout` 识别“关键证据”作为证据锚点，避免错误补第一条 quote。
- `semantic_readout` 对已经写成“观察/继续看/后面看”的 `continue_signal` 不再自动追加英文词。

## 验证

- `python -m py_compile app/services/hotpost/card_content_generator.py app/services/hotpost/semantic_readout.py`
- `pytest tests/services/hotpost/test_reddit_guide_prompt_assets.py tests/services/hotpost/test_card_content_generator.py::test_signal_prompt_budget_keeps_role_readable tests/services/hotpost/test_card_content_generator.py::test_signal_prompt_does_not_ask_llm_to_generate_min_test_action tests/services/hotpost/test_card_content_generator.py::test_generate_json_retries_once_when_gemini_returns_broken_json tests/services/hotpost/test_card_content_generator.py::test_semantic_readout_does_not_append_junk_terms_to_natural_continue_signal -q --tb=short -p no:schemathesis`

结果：6 passed。

## 样本结论

临时生成 3 张潜力快帖样本，不写入 draft store。

- Cursor 多文件依赖：夸张词减少，能讲清“AI 聊天窗口处理复杂工程上下文的上限”。
- PMax Feed：表达顺畅，能讲清“出单产品不等于赚钱，预算需要拆分控制”。
- Claude 原生插件：表达顺畅，能讲清“开发者从厚封装转向原生文件夹/Git 管理”。

当前语义质量比旧版更稳，但仍需要继续观察正式批量出卡里的长尾样本。
