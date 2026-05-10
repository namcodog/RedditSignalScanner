# Design: Signal Prompt Boundary
Date: 2026-04-10
Branch: main

## Problem Statement

Signal 快报现在的主要问题不是某一句文案不好，而是语义主链不清楚。

同一张卡同时被角色 prompt、字段合同、de-ai 规则、禁词门禁、semantic_readout、历史 polish 多层改写，导致输出一会儿像朋友转述，一会儿像质检表，一会儿又被模板打回旧世界。

## Premise Challenges

- 不是前端问题。前端主要负责展示字段，当前读感问题来自字段内容本身。
- 不是单纯模型问题。主模型已经切到 `google/gemini-3.1-flash-lite-preview`，但 prompt 仍被多层规则稀释。
- 不是继续加 YAML 规则能解决。YAML 现在已经混进字段语义、去 AI 味、禁词、pack 指令、后处理替换，继续加会让系统更像补丁仓库。
- 不是 de-ai 越强越好。de-ai 只能改表达，不能改字段语义；否则 why_now / why_test_now 会继续互相污染。

## Options Considered

| Option | What | Effort | Risk | Decision |
|---|---|---:|---:|---|
| A. 继续 YAML 补丁 | 针对坏句子继续加 banned/rewrite | S | High | 不选，会越写越长 |
| B. 单独换模型 | 全部依赖 Gemini 更强语义 | S | Med | 不选，只能缓解，不能修边界 |
| C. 单一语义主链 | 角色 prompt 做主脑，字段语义做骨架，de-ai 只做表达，后处理只做保护 | M | Low | 选 |

## Chosen Direction

采用 Option C：单一语义主链。

目标链路：

```text
source evidence
  -> signal field semantics
  -> reddit guide voice
  -> LLM generation
  -> semantic validation
  -> light normalization
  -> publish
```

对应职责：

- `prompt_assets/`：拥有角色灵魂、字段语义、少量好坏样例。
- `card_content_prompts.py`：只负责组装证据、schema、输出模式，不再承担长篇写法规则。
- `card_content_rules.yaml`：只保留短配置、模型路由、fatal guard、少量 pack 指令，不再做文案补丁仓库。
- `semantic_readout.py`：只做事实保护、轻量清洗和语义校验，不再追加第二套口吻 prompt。
- `card_content_polish.py`：只用于历史卡迁移或手工指定范围，不再默认覆盖新生成卡语义。

## Success Criteria

- 新生成 signal 卡的 `why_now` 和 `why_test_now` 稳定分工：前者讲行动价值，后者讲证据怎么读。
- `continue_signal` 必须包含可继续检索的词、动作或对比，不再出现万能句。
- `stop_signal` 必须是当前话题的退出条件，不再是通用“零散吐槽”。
- prompt 总长度下降，负面规则密度下降，不再用大量“不要”驱动模型。
- YAML 不再继续膨胀成文案规则仓库。
- 历史 polish 不会覆盖新卡主链语义。

## Risks

- 风险 1：拆得太猛会影响现有产卡稳定性。
  - 缓解：先只改 signal 线，并用 5 张真实 signal 卡 A/B。
- 风险 2：禁词从硬拦截改弱后，可能放进少量机器腔。
  - 缓解：保留 fatal guard，只把风格词降级为 warning/rewrite。
- 风险 3：prompt asset 过长也会重新膨胀。
  - 缓解：加 prompt budget 测试，限制长度和“不要”数量。

## NOT in Scope

- 不重做 hot / breakdown。
- 不改前端详情页结构。
- 不改抓取、候选、发布、mini snapshot 链路。
- 不继续用逐句 rewrite 修单条坏样例。

## Implementation Order

1. 建立 `signal_field_semantics` prompt asset，收口字段职责。
2. 精简 `card_content_prompts.py`，让它只拼 evidence/schema/mode。
3. 清理 `card_content_rules.yaml`，把长文案合同迁走，保留配置。
4. 拆分 hard banned 与 style smell，减少误伤。
5. 移除实验链和 polish 链里的 `why_test_now = why_now`。
6. 限制 `polish_published_card` 的作用范围，避免污染新卡。
7. 增加 prompt budget 和字段语义测试。
8. 用 5 张真实 signal 卡做 A/B，再决定是否批量重生成。
