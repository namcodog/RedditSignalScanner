---
name: signal-ops
description: 日常 signal 产卡操作；用于 collect、看 signal 候选、seed draft、人工 review 和发布检查。
---

# Signal Ops

## 何时使用

- 跑日常 signal 产卡
- 看 signal 候选队列
- seed `validate` draft
- 人工 review `信号快报`
- 发布 signal 卡

## 不做什么

- 不重写 signal 生成逻辑
- 不复制 pack 规则
- 不改 prompt
- 不替代优化工作流

## 使用顺序

1. 先读：
   - `docs/sop/2026-04-09-稳态运营成功SOP.md`
   - `docs/sop/2026-04-08-评审与发布SOP.md`
2. 再按这个顺序执行：
   - `make hotpost-publish-until-exhausted`
   - `python backend/scripts/hotpost/review_cards.py queue --type validate --limit 20`
   - 如果这轮是在补薄某个方向，再带 `--scope <scope_id>`
   - 先确认目标 candidate 还没有现成 draft；如果已有 draft，直接 `show-draft` 继续审，不要重复 seed
   - `python backend/scripts/hotpost/review_cards.py seed <candidate_id> validate`
   - 如果目标 candidate 已在原料池里、但还没进当前 queue snapshot，且你已经人工确认这张值得落草稿，可以用：`python backend/scripts/hotpost/review_cards.py seed <candidate_id> validate --live`
   - `seed --live` 只在“还没有 draft”时使用；已有 draft 会直接报 `Draft already exists`
   - `python backend/scripts/hotpost/review_cards.py show-draft <draft_id>`
   - 如果候选确认不该再回队列：`python backend/scripts/hotpost/review_cards.py reject <candidate_id> --reason <reason>`
   - `python backend/scripts/hotpost/review_cards.py publish <draft_id>`
   - `python backend/scripts/hotpost/push_mini_snapshot.py`
   - 如果这轮发现了值得长期追的新社区，补做正式接线：更新 `backend/config/hotpost_supply_discovery_v2.yaml`，再审计 runtime spec 是否已吃到
   - 再回到 `make hotpost-publish-until-exhausted`

## 判断边界

- 自动只到 draft
- 发布继续人工
- 具体卡片质量判断，以当前 backend 代码和正式 judge/gate 为准，不以本 skill 为准
- 日常默认先跑 `all-scope` 基础轮，再做定向补薄；不要一开始就锁死在单一 scope
- 如果候选显示 `lane=hot`，交给 `hot-ops`，不在这里处理
- 如果候选显示 `card_type=write` 或明显更适合拆解，交给 `breakdown-ops`
- 发布前先去掉同题的 `candidate / group / draft` 重复，同天不双发
- 时间窗口默认先看 `7d`
- 只有确认 `7d` 已吃干净、继续深挖净新增变少时，才开 `15d`
- `15d` 只当扩容盘，不和 `7d` 并行默认跑；只有用户明确要求再扩窗时，才开 `30d`
- `1.0` 阶段先追信息密度，不追精选刊物式完稿；但仍然要挡掉：
  - 纯空话
  - 纯模板
  - 纯没信息量
- 发布后必须核对最新 release 已同步到 mini snapshot
- 这轮只有在没有新的净新增价值时才停，不是发一两张就收
