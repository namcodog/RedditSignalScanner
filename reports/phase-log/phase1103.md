# phase1103 - ai-automation 探索 probe 产生候选证据

## 这轮达到的目的
验证 Hotpost 探索社区池不只停在配置 dry-run，而能真实跑出候选证据。

## 当前状态变化
- `probe_community_discovery.py --scope ai-automation --mode safe --max-candidates 5` 已按 `experimental_only` 跑通。
- 发现 `r/CursorAI` 2 条候选证据、`r/windsurf` 1 条候选证据，均映射到 `AI工具与Agent`。
- R11 dry-run 仍为 `input_rows=16 / already_in_pool=3 / keep_testing=13 / promote_candidate=0 / reject=0`。
- 修正 probe CLI JSON 输出、`experimental_only` 显式字段筛选和 dry-run 风险备注去重，报告不再把逗号备注当成一条风险。

## 还没完成什么
- 候选还没进入 draft / published，所以没有社区满足 R12 Dev 写入闸门。
- `r/aider`、`r/openrouter` 仍是 `no_signal_yet`。

## 下一步做什么
先 review / seed `CursorAI` 和 `windsurf` 候选，确认能否进入 draft / publish；有发布证据后再重跑 R11 并决定 R12。
