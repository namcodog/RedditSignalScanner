# Phase 743

## 时间

- 2026-04-10 00:23 CST

## 本轮目标

- 把 `1.0` 新共识继续收进执行入口
- 避免旧的 `20 张 / 10-6-4 / 7-7-6` 口径继续误导日常运营

## 实际完成

1. 更新工作流 skill
   - [signal-ops/SKILL.md](/Users/hujia/Desktop/RedditSignalScanner/.agents/skills/signal-ops/SKILL.md)
   - [hot-ops/SKILL.md](/Users/hujia/Desktop/RedditSignalScanner/.agents/skills/hot-ops/SKILL.md)
   - [breakdown-ops/SKILL.md](/Users/hujia/Desktop/RedditSignalScanner/.agents/skills/breakdown-ops/SKILL.md)
   - 统一改成：
     - `1.0` 密度优先
     - collect 默认 `--mode harvest`
     - publish 后必须核对 mini snapshot release

2. 更新仓库级规则
   - [AGENTS.md](/Users/hujia/Desktop/RedditSignalScanner/AGENTS.md)
   - 当前正式口径改成：
     - 最近 `30` 张窗口
     - lane：`18 / 8 / 4`
     - scope：`10 / 10 / 10`
     - 每天 `5` 次上新
     - 每次至少新增 `6` 张
     - 每天累计至少新增 `30` 张

3. 旧文档去误导
   - [2026-04-09-lane-mix-design.md](/Users/hujia/Desktop/RedditSignalScanner/docs/superpowers/specs/2026-04-09-lane-mix-design.md)
   - [2026-04-09-hot-supply-and-lane-audit.md](/Users/hujia/Desktop/RedditSignalScanner/docs/superpowers/specs/2026-04-09-hot-supply-and-lane-audit.md)
   - 两份都补了“历史材料 / 已被新合同替代”的头注

## 验证

- [test_card_selection_policy.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_card_selection_policy.py)
  - `6 passed`

- 当前真实最近 `30` 张：
  - lane：`24 / 5 / 1`
  - scope：`12 / 10 / 8`

## 结论

- 现在“1.0 密度优先”不再只是口头共识，已经进了合同、SOP、技能入口和调度器
- 当前主矛盾进一步明确：
  - 不是标准太严
  - 是 `signal` 仍然吃掉窗口，`hot + breakdown` 供给不够

## 下一步

1. 不再继续补 `signal`
2. 优先补 `hot`
3. 再补 `breakdown`
4. 开始按“每天 5 次上新、每天 30 张新增”去倒推运营节奏
