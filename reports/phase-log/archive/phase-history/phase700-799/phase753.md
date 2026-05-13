# Phase 753 - 信号快报详情页语义 A/B 小闭环

日期：2026-04-10

## 发现了什么

- 当前信号快报的 AI 味不是单点问题：
  - 后端生成字段会产出模板句，例如“如果接下来在更多社区里还出现同样抱怨”。
  - `summary_line` prompt 会诱导“这帖吵的不是 A，而是 B”。
  - 前端详情页标题把字段包装成问卷式问题，例如“是谁在这个场景里反复提这件事”“哪些关键词说明事情在变严重”。
- 当前 release 里 48 张 signal validate 卡中：
  - 31 张命中“如果接下来在更多社区里还出现同样抱怨”
  - 32 张命中“如果后面只剩零散吐槽”
  - 45 张命中“就继续盯”
  - 48 张命中“先放过”

## 是否需要修复

需要。否则详情页继续像审稿表，用户读不到具体信号，只会看到正确但无信息量的模板句。

## 精确修复方法

- `backend/config/card_content_rules.yaml`
  - 加强 `generation_field_contract.summary_line`
  - 要求 `continue_signal` 必须包含当前话题里的具体关键词、动作或争议点
  - 增加字段级 banned patterns，拦截：
    - “这帖吵的不是”
    - “这帖问的是”
    - “如果接下来在更多社区里还出现同样抱怨”
    - “如果后面只剩零散吐槽”
- `backend/app/services/hotpost/card_content_generator.py`
  - `_validated_text()` 增加字段级 banned pattern 校验
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.tsx`
  - 信号快报详情标题改成更低认知负担的标签：
    - “核心卡点”
    - “用户画像”
    - “为什么现在值得看”
    - “继续看哪些迹象”
    - “什么时候可以先放下”
- `backend/tests/services/hotpost/test_card_content_generator.py`
  - 增加报告腔 summary 拦截测试
  - 增加万能 continue/stop 拦截测试

## 验证

```bash
python -m py_compile backend/app/services/hotpost/card_content_generator.py backend/app/services/hotpost/card_content_prompts.py backend/app/services/hotpost/card_content_generation_contract.py
pytest backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_semantic_readout_boundary.py -q --tb=short -p no:schemathesis
cd hotpost-mini/hotpost-mini-app && npm run build:weapp
```

结果：

- 后端语义测试：`38 passed`
- 小程序构建：`Compiled successfully`

## 下一步

- 用 Cursor 信号做一张重生成样例，确认字段读感是否比旧卡更像人话。
- 如果样例通过，再批量重生成信号快报并同步 release。
