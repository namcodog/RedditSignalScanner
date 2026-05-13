# Phase 752 - P1/P2 语义输出合同接入生成链路

日期：2026-04-10

## 发现了什么

- P1 的 `continue_signal / stop_signal` 必填校验已经在生成主链生效，不能再用模板兜底把 LLM 漏字段伪装成成功。
- P2 不能继续先动小程序详情页结构。上一轮 `detail-sections.tsx` 虽然构建通过，但用户看到白屏，说明前端产品态优化必须先保护基线。
- 当前更安全的 P2 入口是后端语义合同：把“讲人话、字段怎么写”的要求配置化，再统一注入生成 prompt。

## 是否需要修复

需要。否则后续卡片语义仍依赖散落在 Python prompt 里的长句约束，既难维护，也容易出现“合同写了，但某条生成链没吃到”的问题。

## 精确修复方法

- 新增 `backend/app/services/hotpost/card_content_generation_contract.py`
  - 负责从 `card_content_rules.yaml` 读取 `generation_field_contract`
  - 输出统一的字段写法合同 prompt
- 更新 `backend/config/card_content_rules.yaml`
  - 增加 `generation_field_contract`
  - 覆盖 `summary_line / pain_point / target_user_and_scene / why_test_now / continue_signal / stop_signal`
  - 明确禁止万能句，要求绑定当前 Reddit 话题里的关键词、动作或争议点
- 更新生成链路：
  - `card_content_generator.py`
  - `card_content_prompts.py`
  - `signal_skill_experiment.py`
- 补测试：
  - YAML 合同能被加载
  - hot 出卡 prompt 确实带上字段写法合同

## 验证

```bash
python -m py_compile backend/app/services/hotpost/card_content_generation_contract.py backend/app/services/hotpost/card_content_prompts.py backend/app/services/hotpost/card_content_generator.py backend/app/services/hotpost/signal_skill_experiment.py
pytest backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_semantic_readout_boundary.py -q --tb=short -p no:schemathesis
```

结果：

- `36 passed`

## 下一步

- 暂不继续改小程序详情页结构。
- 下一轮应先用一批本地候选实际生成卡片，对比 `summary_line / continue_signal / stop_signal` 是否更像人话。
- 如果语义仍拗口，再收紧 YAML 字段合同，而不是在前端补文案掩盖。
