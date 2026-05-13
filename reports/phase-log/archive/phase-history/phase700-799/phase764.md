# Phase 764 - Signal 语义合同接回主链

## 发现

- `signal_field_semantics.md` 之前只在测试里读取，没有真正进入 `signal` 运行时 prompt。
- `build_generation_field_contract_prompt()` 仍然返回空串，所以“字段边界合同”实际没有进主链。
- 这就是为什么前面明明在改 prompt 资产，真实样本还是会漂：系统只吃到了 `signal_compact_prompt.md`。

## 修复

- 在 `backend/app/services/hotpost/reddit_guide_prompt_assets.py` 里，把 `signal_field_semantics.md` 正式接回 `潜力快帖` 的 prompt prefix。
- 重写 `backend/config/prompt_assets/signal_compact_prompt.md`：
  - 收成角色、总写法、证据强弱、输出字段四层
  - 减少负向禁令
  - 明确“信息颗粒度可以留，但顺序要排好”
- 重写 `backend/config/prompt_assets/signal_field_semantics.md`：
  - 明确字段职责
  - 增加“单个用户给出的解法，只能写成一个方向，不是唯一答案”
  - 增加好坏写法对照
- 升级 `/Users/hujia/.codex/skills/de-ai-writer/SKILL.md`：
  - 把“单条证据不要写满”的规则写成技能合同
  - 加入好坏例句，约束 summary/one_liner 的强度

## 验证

- `pytest backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py backend/tests/services/hotpost/test_card_content_generator.py::test_signal_prompt_budget_keeps_role_readable -q --tb=short -p no:schemathesis`
  - `3 passed`
- `signal` prompt 当前运行时统计：
  - `len = 2264`
  - `不要 = 4`
- 抽样 dry-run：
  - `backend/tmp/signal-semantic-recheck-3cards.json`
  - 三张样本的整体语气、结构和逻辑都明显比旧版顺
  - 仍有余量的点主要是：`audience` 偶尔偏长，`why_test_now` 有时还会保留较强的英文原话

## 当前判断

- 这次不是简单润色，而是把 `signal` 的语义合同真正接回了主链。
- 后面继续调语义时，改的已经是“真实生效的合同”，不是只改测试资产。
