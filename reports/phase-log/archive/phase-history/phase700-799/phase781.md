# phase781

## 事项

- 回灌 `hot sample-boundary v7`
- 回灌 `hot fight-line-definition v3`
- 不扩 schema，继续使用现有 `hot / signal` 二分类

## 本次改动

- 入口边界
  - `backend/app/services/hotpost/card_lane_policy.py`
  - `backend/config/hotpost_supply_discovery_v2.yaml`
  - `backend/app/services/hotpost/hotpost_supply_contract.py`
- hot prompt 资产
  - `backend/config/prompt_assets/hot_compact_prompt.md`
  - `backend/config/prompt_assets/hot_field_semantics.md`
- 最小运行时补口
  - `backend/app/services/hotpost/semantic_readout.py`
  - 只补了自动锚点跳过 `TL;DR of the discussion generated automatically ...` 这类 AI-summary quote
- 测试
  - `backend/tests/services/hotpost/test_card_lane_policy.py`
  - `backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py`
  - `backend/tests/services/hotpost/test_card_content_generator.py`

## 实际回灌规则

### sample-boundary v7 -> 生产二分类

- `hot_keep + hot_borderline => hot`
- `signal_not_hot => signal`
- `reject => 继续走现有过滤逻辑`
- 不新增 `hot_borderline` 状态

具体落地：

- 评论多不再直接等于 hot
- 双边对打不是 hot 必要条件
- 多人围绕同一件事报动作 / 报损失 / 报迁移 / 报退订，即使标题是提问句，也允许进 hot
- 官方发布 / 平台动作但仍处围观、试探、怀疑早期，在当前结构里继续先进 hot 复核侧
- practical share / direct question 继续留 signal
- 纯观点、趣闻、轻情绪，不因热度高就升 hot

### fight-line-definition v3 -> hot prompt

- 冲突线优先于情绪
- `fight_line` 必须能压成一句对打句
- 不要求双方声量对称
- 只要第二种解释框架或反对方向持续出现，就不要压成纯情绪
- 方法 / 优先级之争只有主轴稳定时才算 `fight_line`
- `why_now` 不扩成行业判断
- 不把 `fight_line` 写成“大家都在骂 / 都在惊讶”的情绪播报

## 回滚点

- `backend/tmp/hot-reinject-backups/20260412-175836`

## 最小验证

### 1. 定向测试

- `python -m py_compile backend/app/services/hotpost/card_lane_policy.py backend/app/services/hotpost/hotpost_supply_contract.py`
- `python -m py_compile backend/app/services/hotpost/semantic_readout.py`
- `pytest backend/tests/services/hotpost/test_card_lane_policy.py backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py backend/tests/services/hotpost/test_card_content_generator.py -q --tb=short -p no:schemathesis`
- 结果：`90 passed`

### 2. lane dry run

- 候选池 `backend/data/hotpost/candidates/*.json`
  - 总计 `15`
  - 新规则下：`hot 5 / signal 10 / error 0`
- 指定 queue 快照 `queue-20260411140247-10dcaf81.json`
  - 总计 `16`
  - 新规则下：`hot 9 / signal 7 / error 0`

判断：

- hot 没有异常膨胀
- 明显 practical / direct question 样本仍留在 signal

### 3. hot output spot check

同一批 hot 候选分别做了 spot check：

- 按当前 hot 生产链（Gemini 3 lane override）抽样
- 再强制切到 `mimo` 做同批抽样

结论：

- 回灌本身成立，不只是 Gemini 3 文风在托
- `mimo` 下的 `fight_line` 更稳、更像对打句
- spot check 暴露了一个旧问题：
  - 运行时自动锚点会把 `TL;DR of the discussion generated automatically ...` 这种 AI-summary 当证据塞进 `why_test_now`
  - 已用最小过滤修掉，不改 schema，不大改 `card_content_rules.yaml`

### 4. signal leak 检查

明显 signal 样本未被大面积误升：

- `I built CLI-Anything-WEB ...` -> signal
- `We need to admit that writing a five thousand word system prompt is not software engineering.` -> signal
- `Anyone know if there are actual products built around Karpathy’s LLM Wiki idea?` -> signal
- `Andrej Karpathy drops LLM-Wiki` -> signal
- `Claude Mythos: The Model Anthropic is Too Scared to Release.` -> signal

## 结论

- 建议正式启用

原因：

- hot 数量没有异常膨胀
- 明显 signal 没被大面积误升
- `fight_line` 明显更接近“冲突线”，不是单纯情绪播报
- 没看到新的模板腔回潮
- 运行时唯一漏口已用最小过滤补住
