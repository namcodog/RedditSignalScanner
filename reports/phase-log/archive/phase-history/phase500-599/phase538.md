# Phase 538 - Hotpost 状态机合同收口

## 发现了什么？

这轮之前，Hotpost 虽然已经有了：

- query planner
- retrieval precision
- evidence package
- core + mode prompts

但还有一个核心问题没有真正落地：

- 系统还没有把 `未命中 / 命中但证据有限 / 命中且证据充分` 三件事彻底分开

现实后果就是：

- 有些地方还在用 `evidence_count` 直接代替状态判断
- reasoning 触发、reliability note、输出收缩，容易混成一团
- mode 容易继续漂移

## 是否需要修复？

需要，而且这轮已经修完。

这不是新功能，而是把我们前面已经聊透的 contract 正式落成代码。

## 精确修复方法

### 1. 新增轻量状态机模块

新增：

- `backend/app/services/hotpost/mode_contract.py`

职责只有一个：

- 根据 mode 和当前证据，判断：
  - `no_hit`
  - `preview`
  - `standard`

并按配置做最小输出投影。

当前行数：

- `mode_contract.py = 191`

### 2. 把阈值正式拆成 3 组

在 `backend/config/hotpost_quality.yaml` 新增：

- `mode_contracts.trending`
- `mode_contracts.rant`
- `mode_contracts.opportunity`

每个 mode 都拆成：

- `hit_rules`
- `sufficiency_rules`
- `projection_rules`

也就是说，系统现在终于把：

- “是否真的命中”
- “证据是否已经足够完整输出”
- “当前应该怎么收缩结果”

这三件事拆开了。

### 3. 让 response bundle 正式吃这层 contract

修改：

- `backend/app/services/hotpost/response_bundle.py`

现在流程变成：

1. merge llm report
2. mode enrich
3. apply mode contract
4. apply quality contract

这意味着：

- `reliability_note` 不再只看 `evidence_count < 10`
- `debug_info` 现在会正式记录：
  - `mode_state`
  - `mode_state_reasons`

### 4. 模式投影规则

当前 contract 已经支持：

- `no_hit`
  - 清掉 mode 的核心输出字段，不再假装有完整洞察
- `preview`
  - 只保留最强的 1-2 个核心项
  - 同时裁剪 `top_quotes`
- `standard`
  - 保留标准输出规模

### 5. 新增测试

新增：

- `backend/tests/services/hotpost/test_hotpost_mode_contract.py`

并补强：

- `backend/tests/services/hotpost/test_hotpost_response_bundle.py`

## 验证

```bash
pytest backend/tests/services/hotpost/test_hotpost_mode_contract.py \
  backend/tests/services/hotpost/test_hotpost_response_bundle.py \
  backend/tests/services/hotpost/test_hotpost_prompts.py \
  backend/tests/services/hotpost/test_hotpost_evidence_package.py \
  backend/tests/services/hotpost/test_hotpost_report_workflow.py \
  backend/tests/services/hotpost/test_hotpost_search_workflow.py -q
```

结果：

- `26 passed`

## 下一步系统性的计划是什么？

Hotpost 现在已经把“拿料准”和“状态判断”这两层接清楚了。

下一步只做最后一段：

- 小样本高价值输出模式

主攻：

- `top_quotes` 的代表性
- `market_opportunity` 的动作化表达
- 让 `preview` 态输出更少、更硬、更能指导下一步动作

## 这次执行的价值是什么？

这轮真正完成的是：

- Hotpost 不再把 `evidence_count` 当成万能阈值
- `no_hit / preview / standard` 已经正式变成主链 contract
- mode 的判断、充分性、输出规模终于分层了

这一步做完后，后面再收输出层，就不会继续因为状态口径不清而漂移。
