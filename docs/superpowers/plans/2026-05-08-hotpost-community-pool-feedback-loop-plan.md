# Hotpost To Community Pool Feedback Loop Plan

日期：2026-05-08
状态：待执行计划

## 目标

把 Hotpost 发现的新长尾社区，安全回流到主项目 `community_pool`，再让社区推荐系统自动读到。

当前不做前端、不做 API、不写 Gold DB、不自动入池。

## 已核实事实

- `experimental_communities` 已存在于 `backend/config/hotpost_supply_discovery_v2.yaml`。
- 默认 `build_reddit_search_specs(scope)` 不包含探索社区。
- 显式 `include_experimental=True` 才会用小配额生成探索 specs。
- `community_discovery_audit` 是只读报告，合同为 `auto_promote=false / writes_db=false`。
- 最新审计 `row_count=16`，全部是 `keep_testing`，说明探索池结构成立，但还没有真实产出证据。
- 当前采集主链 `collect_scope_candidates_with_summary()` 仍调用默认 specs，没有把探索社区接进任何显式试采命令。

## 数据流

```text
experimental_communities
  -> explicit probe collect
  -> candidates / drafts / published / rejected
  -> community discovery audit
  -> community_pool feedback dry-run
  -> manual review
  -> Dev community_pool write
  -> recommendation preview refresh
```

## R10：显式探索试采入口

目标：让探索社区能被小配额试采，但 daily collect 默认不受影响。

最小改动：
- 给 Hotpost 采集服务加 `include_experimental=False` 参数。
- 新增或扩展一个显式 probe 命令，只在人工触发时打开探索社区。
- 保持 `daily_collect`、freshness gate、日常出卡默认不包含探索社区。

验收：
- 默认采集 specs 不出现 `experimental_`。
- 显式 probe specs 出现探索社区，且社区数和 specs 数受 `experimental_collect` 限制。
- 相关测试覆盖默认隔离和显式打开两条路径。

## R11：回流 dry-run 规划器

目标：把 Hotpost 探索结果变成“是否建议入池”的只读报告。

输入：
- `community-discovery-audit-YYYY-MM-DD.json`
- Dev `community_pool`
- `community_interest_tags.json`
- Hotpost published / candidate / rejected 证据

输出：
- `already_in_pool`
- `promote_candidate`
- `keep_testing`
- `reject`

每行必须包含：
- 社区名、来源 scope、topic cluster
- 候选数、草稿数、发布数、拒绝数、重复数
- 建议映射到的用户标签
- 推荐理由和风险
- 是否已经在 `community_pool`

验收：
- 只读，不 `commit`。
- 不硬编码用户标签。
- 没有证据的社区只能 `keep_testing`，不能入池。

## R12：Dev 写入闸门

目标：用户审核 dry-run 后，才允许写 Dev `community_pool`。

最小改动：
- 复用 Phase 2 Dev 写入 guard 和 rollback 思路。
- 只写 `reddit_signal_scanner_dev`。
- 每次写入都生成 rollback SQL。
- 已存在、黑名单、删除冲突社区必须跳过或阻断。

验收：
- Gold DB 默认禁止。
- 写入前后 active count 可验证。
- rollback SQL 只覆盖本次新增。

## R13：推荐系统刷新

目标：新入池社区能进入当前 9 个标签推荐链。

步骤：
- 重跑 `community_recommendation_preview.py`。
- 检查新社区是否映射到对应用户标签。
- 检查用户文案不暴露 `Hotpost / community_pool / semantic_observation` 等内部词。

验收：
- `preview.md/json` 和 `audit.md/json` 更新。
- 新社区不是库存清单式展示，必须有理由和证据。

## R14：运营闭环

目标：把这条链固化成轻量 SOP。

节奏：
- 日常出卡不受影响。
- 探索试采按需手动跑。
- 每次只从 dry-run 审核通过的社区写 Dev。
- 推荐质量验收通过后，再考虑 API / 前端。

## 非目标

- 不自动把探索社区写入 `community_pool`。
- 不让小程序直接写社区池。
- 不新建复杂表结构。
- 不把 Hotpost card count 当唯一入池门槛。
- 不把没有出卡的旧 DB 社区降级或删除。
