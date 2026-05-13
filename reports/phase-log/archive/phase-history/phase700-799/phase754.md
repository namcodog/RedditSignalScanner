# Phase 754 - de-ai-writer 合同接入卡片生成 prompt

日期：2026-04-10

## 发现了什么

- Phase 753 已经解决了字段边界和万能句门禁，但 `generation_field_contract` 还偏“字段说明”，缺少 `de-ai-writer` 的写作层规则。
- 如果不把 `de-ai-writer` 规则沉进 prompt，后续仍可能出现机械连接词、报告腔句式、总结段和漂亮废话。

## 是否需要修复

需要。语义优化不能停留在单张卡人工改写，必须进入生成主链。

## 精确修复方法

- `backend/config/card_content_rules.yaml`
  - 新增 `de_ai_writer_contract`
  - 包含：
    - 事实不变，不补证据
    - 能短就短，能具体就具体
    - 不写总结段、升华段、正确废话
    - 少用机械连接词和“不是 A 而是 B”模板
  - `banned_patterns.global` 增加：
    - `首先`
    - `其次`
    - `再次`
    - `综上`
    - `总的来说`
    - `值得注意的是`
    - `从某种意义上说`
    - `随着`
    - `引发热议`
- `backend/app/services/hotpost/card_content_generation_contract.py`
  - `build_generation_field_contract_prompt()` 同时输出：
    - `de-ai-writer 写作合同`
    - `字段写法合同`
- `backend/tests/services/hotpost/test_card_content_generator.py`
  - 验证 prompt 确实包含 `de-ai-writer 写作合同`
  - 增加机械 AI 连接词拦截测试

## 验证

```bash
python -m py_compile backend/app/services/hotpost/card_content_generation_contract.py backend/app/services/hotpost/card_content_generator.py
pytest backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_semantic_readout_boundary.py -q --tb=short -p no:schemathesis
```

结果：

- `39 passed`

## 下一步

- 用 Cursor 信号做真实重生成 A/B，而不是继续只看手写样例。
- 如果新生成结果稳定，再批量重生成 signal 详情字段并同步 release。
