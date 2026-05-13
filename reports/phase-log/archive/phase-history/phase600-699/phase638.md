# Phase 638 - 卡片口径精修与已发布卡批量清洗

## 1. 发现了什么

- 新卡主链已经切到“需求信号卡”口径，但已发布 34 张卡里还残留两类脏东西：
  - 内部规则词直接出现在展示文案里，比如 `switch_signal_7d`、`recurring_7d`、`new_threads_24h`
  - 明显的报告腔和 AI 腔，比如“根本矛盾”“心理摩擦力”“蜕变”“反人性”
- 真正的问题不在 schema，也不在接口，而在内容生成后的最后一层口径约束不够硬。

## 2. 是否需要修复

需要，而且必须同时修两层：

1. 未来新卡：生成器要直接禁掉内部标签和报告腔
2. 已发布旧卡：要做一次确定性批量清洗，否则前端已经换了新口径，内容还会继续穿帮

## 3. 精确修复方法

### 后端生成链

- 新增 [backend/app/services/hotpost/card_content_polish.py](../../backend/app/services/hotpost/card_content_polish.py)
  - 统一做人话化清洗
  - `why_now / why_test_now / continue_signal / stop_signal` 改成结构化拼句，不再信任 LLM 直出
  - 补了少量高价值卡的定向重写，专门收拾最重的“报告腔”
- 修改 [backend/app/services/hotpost/card_content_generator.py](../../backend/app/services/hotpost/card_content_generator.py)
  - 信号卡的 `why_now` 和 `detail.why_test_now` 改成由结构化字段生成
  - `continue_signal / stop_signal` 改成固定规则生成
  - 所有标题/摘要/受众/拆解字段进库前统一走清洗
- 修改 [backend/app/services/hotpost/card_content_prompts.py](../../backend/app/services/hotpost/card_content_prompts.py)
  - 明确禁止输出内部规则词
  - 明确禁止“根本矛盾”“核心问题并非”“反直觉工作流”这类咨询报告腔
- 修改 [backend/config/card_content_rules.yaml](../../backend/config/card_content_rules.yaml)
  - banned patterns 扩充到内部 token + 常见 AI 腔

### 已发布数据

- 新增 [backend/scripts/polish_hotpost_cards.py](../../backend/scripts/polish_hotpost_cards.py)
  - 对 `backend/data/hotpost_clues.json` 的 34 张 published 卡做批量精修
- 已执行：
  - `python scripts/polish_hotpost_cards.py`
  - 结果：`{"polished": 34}`

### 测试

- 新增和更新测试：
  - [backend/tests/services/hotpost/test_card_content_generator.py](../../backend/tests/services/hotpost/test_card_content_generator.py)
- 已验证：
  - `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_content_generator.py backend/tests/api/test_hotpost_card_candidates.py backend/tests/api/test_hotpost_card_review.py backend/tests/api/test_hotpost_clues.py -q`
  - 结果：`19 passed`

## 4. 当前结果

- 前端展示文案里不再出现 `switch_signal_7d / recurring_7d / new_threads_24h / signal_level`
- “热点 / 升温 / 持续” 这条时间维度仍然保留在 `signal_level`
- `why_now` 统一变成用户能直接看懂的句子：社区、帖子数、最近是否继续冒头、讨论是在吐槽还是已经开始找替代
- 最重的几张卡已经从“咨询报告腔”收回到“人话信号卡”口径
- 运行态也已对齐：
  - 发现 API 测试会把 `backend/data/hotpost_clues.json` 回滚成测试种子
  - 发现原 `make dev-backend-start` 包装链下的 8006 进程一度没有对齐到最新卡片源
  - 现已在测试后重新落盘，并用直接可验证的 uvicorn 启动方式重起 8006，接口实测返回新卡内容

## 5. 剩余风险

- 这轮清洗已经把最脏的口径拿掉，但个别卡的洞察力度仍然有提升空间，后续应该继续用真实卡片抽样来迭代 prompt，而不是再靠人工逐张救火。

## 6. 这次执行的价值

- 把“需求信号卡”从口号变成了真正稳定的内容合同
- 把旧卡和新卡的口径拉回到同一条线上
- 后面再生成新卡时，不会再把内部规则名和报告腔直接喷到用户面前
