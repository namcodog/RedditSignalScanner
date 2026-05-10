# Phase 537 - Hotpost Core Prompt 与 Mode Profile 收口

## 发现了什么？

这轮之前，Hotpost 的主链已经基本稳定，但还有两个结构性问题：

1. `evidence_package.py` 超过了当前轻量模块的体量约束，不利于继续低耦合演进。
2. prompt 还是一整块大字符串，`trending / rant / opportunity` 的口径虽然在用，但没有被真正拆成共享 core 和 mode profile。

另外，旧 prompt 还在要求模型输出这些系统不会消费的顶层字段：

- `confidence`
- `evidence_count`
- `community_distribution`

这会让模型输出合同和 `sanitize_llm_report()` 的真实消费口径继续错位。

## 是否需要修复？

需要，而且这轮已经修完。

这不是为了“写得更好看”，而是为了把 Hotpost 的模式边界锁死，避免后面继续漂移。

## 精确修复方法

### 1. 拆轻 evidence packaging

把超长的 `evidence_package.py` 拆成两层：

- `backend/app/services/hotpost/evidence_focus.py`
- `backend/app/services/hotpost/evidence_package.py`

现在的职责更清楚：

- `evidence_focus.py`
  - 负责 query/domain/focus term 的计算
  - 负责 post/comment 打分
  - 负责关键 quote 抽取
- `evidence_package.py`
  - 只负责把高分证据组装成 LLM 输入包

文件行数：

- `evidence_focus.py = 141`
- `evidence_package.py = 133`

### 2. 把 prompt 收成 core + 3 mode profiles

新增：

- `backend/app/services/hotpost/prompt_core.py`
- `backend/app/services/hotpost/prompt_trending.py`
- `backend/app/services/hotpost/prompt_rant.py`
- `backend/app/services/hotpost/prompt_opportunity.py`

并把 `backend/app/services/hotpost/prompts.py` 收成兼容层，只负责聚合导出：

- `BASE_RULES`
- `TRENDING_PROMPT`
- `RANT_PROMPT`
- `OPPORTUNITY_PROMPT`
- `PROMPT_TEMPLATES`

这样做的结果是：

- workflow 仍然只 import `prompts.py`
- mode 口径已经真正拆开
- shared core 不再散落到各 mode 里重复维护

### 3. 对齐 prompt 与 sanitize 的真实合同

这轮 prompt 已经移除了不会被系统消费的顶层字段要求：

- 不再要求 `confidence`
- 不再要求 `evidence_count`
- 不再要求 `community_distribution`

同时补了一个之前缺失但系统会消费的输出点：

- `opportunity` 现在会主动要求 `top_quotes`

## 验证

### 行数约束

- `prompt_core.py = 46`
- `prompt_trending.py = 57`
- `prompt_rant.py = 92`
- `prompt_opportunity.py = 106`
- `prompts.py = 22`
- `evidence_focus.py = 141`
- `evidence_package.py = 133`

全部都在当前轻量边界内。

### 测试

```bash
pytest backend/tests/services/hotpost/test_hotpost_prompts.py \
  backend/tests/services/hotpost/test_hotpost_evidence_package.py \
  backend/tests/services/hotpost/test_hotpost_report_workflow.py \
  backend/tests/services/hotpost/test_hotpost_search_workflow.py \
  backend/tests/services/hotpost/test_hotpost_runtime_config.py -q
```

结果：

- `21 passed`

## 下一步系统性的计划是什么？

Hotpost 现在不该再回头折腾架构，也不该继续散着改规则。

下一步固定只做一件事：

- 继续收 `low-sample high-value` 输出模式

重点是：

- `top_quotes` 的代表性
- `market_opportunity` 的动作化表达
- `trending / rant / opportunity` 各自在小样本下只保留最硬的 1-2 个信号

## 这次执行的价值是什么？

这轮真正完成的是“模式合同收口”。

从现在开始，Hotpost 的结构更清楚了：

- `core` 负责共用判断原则
- `trending / rant / opportunity` 各自只回答自己的问题
- workflow 不需要知道 prompt 细节
- prompt 不再要求系统根本不会消费的字段

这意味着后面继续提质时，系统不会再一边调算法、一边让 mode 边界继续漂。
