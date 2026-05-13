---
name: hot-ops
description: 日常 hot 爆贴产卡操作；用于审计 runtime hot、筛 lane=hot 候选、seed draft、人工 review 和发布。
---

# Hot Ops

## 何时使用

- 跑日常 `爆贴热点`
- 看 `runtime hot` 候选
- seed `validate` 热点 draft
- 人工 review 热点卡
- 发布热点卡

## 不做什么

- 不重写 hot lane 生成逻辑
- 不复制 pack 规则
- 不改 prompt
- 不替代优化工作流

## 使用顺序

1. 先读：
   - `docs/sop/2026-04-09-爆贴热点运营SOP.md`
   - `docs/sop/2026-04-08-评审与发布SOP.md`
2. 再按这个顺序执行：
   - `make hotpost-workflow-dry-run`
   - `make hotpost-publish-until-exhausted`
   - `python backend/scripts/hotpost/audit_hot_lane.py`
   - `python backend/scripts/hotpost/review_cards.py queue --type validate --limit 20`
   - 如果这轮是在补薄某个方向，再带 `--scope <scope_id>`
   - 只处理输出里 `lane=hot` 的候选
   - 先确认目标 candidate 还没有现成 draft；如果已有 draft，直接 `show-draft` 继续审，不要重复 seed
   - `python backend/scripts/hotpost/review_cards.py seed <candidate_id> validate`
   - 如果目标 candidate 已确认值得做 `hot`，但没进当前 queue snapshot，可以用：`python backend/scripts/hotpost/review_cards.py seed <candidate_id> validate --live`
   - `seed --live` 只在“还没有 draft”时使用；已有 draft 会直接报 `Draft already exists`
   - `python backend/scripts/hotpost/review_cards.py show-draft <draft_id>`
   - 如果候选确认不该再回队列：`python backend/scripts/hotpost/review_cards.py reject <candidate_id> --reason <reason>`
   - `python backend/scripts/hotpost/review_cards.py publish <draft_id>`
   - `python backend/scripts/hotpost/push_mini_snapshot.py`
   - 如果这轮的热点来自新社区且后续还想持续采，补做 discovery 接线审计
   - 再回到 `make hotpost-publish-until-exhausted`

## 当前稳定边界

- `hot` 现在不是“所有高热帖都能进”
- 先看 `runtime hot` 审计，再看 queue
- `search / listing` 只是检索方式，不是热点定义
- 日常默认先跑 `all-scope` 基础轮，再做定向补薄；不要只围着一个老社区打转
- 时间窗口默认先看 `7d`；只有确认 `7d` 已吃干净后，才开 `15d` 做扩容
- `1.0` 阶段先追信息密度，不追后期精选杂志那种完稿强度
- 只要帖本身够热、讨论焦点够清楚、又不是水帖，就可以进 `hot` review
- 发布后必须核对最新 release 已同步到 mini snapshot
- 这轮只有在没有新的净新增价值时才停，不是发一两张就收

## 判断边界

- `爆贴热点` 继续属于 `validate + lane=hot`
- 自动只到 draft
- 发布继续人工
- 只看：
  - 这帖为什么火
  - 大家主要在吵什么
  - 争议是不是够具体
- review 时默认把草稿收成：
  - 标题先说这帖为什么火
  - summary 直接讲争议点
  - why_now 讲讨论为什么已经变成路线分歧
- 如果同题已经有 `signal / breakdown` 替代版，`hot` 默认只保留一个主发位，不同题材再并发
- `hot` 只要过水线就尽快发，不要审到接近 `breakdown`
- `1.0` 阶段允许 `hot` 比 `signal` 更短、更直接，只要读起来顺、信息够、不是垃圾帖
- 如果这轮没有像样的 `lane=hot` 候选，就停，不为补量硬发

## 必须拒绝

- 围观型怀旧帖
- 纯情绪发泄
- 纯意识形态对线
- 事件本身大，但评论区没有展开
- 高信息密度实操分享，但没有争议焦点
