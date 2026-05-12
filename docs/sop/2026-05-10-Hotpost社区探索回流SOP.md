# Hotpost 社区探索回流 SOP

日期：2026-05-10
适用范围：Hotpost / 小程序日常出卡后，把探索社区安全回流到主项目 `community_pool` 的流程。

## 一句话口径

探索社区先证明价值，再进入主项目社区池；任何阶段都不自动写 DB。

## 固定边界

- 正式日常出卡仍走 `daily_collect` / V13 review / publish 主链。
- 探索社区只来自 `backend/config/hotpost_supply_discovery_v2.yaml` 的 `experimental_communities`。
- 默认日常采集不包含 `experimental_communities`。
- probe 候选只允许写 `backend/data/hotpost/experimental_candidates/<scope>.json`。
- 回流报告、R11.5、R12 预审都只读，不能写 `community_pool`。
- Gold DB 禁止写；Dev 写入必须单独确认、带 guard 和 rollback。
- 小程序只读发布快照，不参与社区池写入。

## 每日标准流程

### 1. 出卡计划同步探索目标

日常出卡计划里必须写明：

- 今天正式出卡补哪些 scope / 题材
- 今天 probe 哪些 scope 或实验社区
- 如果不 probe，写明原因

### 2. 显式 probe

只允许显式运行：

```bash
PYTHONPATH=backend python backend/scripts/hotpost/probe_community_discovery.py --scope <scope_id> --mode safe --max-candidates <n>
```

禁止把 `experimental_communities` 接进默认 `daily_collect`。

### 3. 生成探索审计

```bash
PYTHONPATH=backend python backend/scripts/hotpost/audit_community_discovery.py
```

重点看：

- `collected_candidates`
- `draft_count`
- `published_count`
- `duplicate_count`
- `new_topic_count`
- `suggested_action`

只说“探索已触发”不合格，必须说明是否有候选和发布证据。

### 4. 生成 R11.5 回流 dry-run

```bash
PYTHONPATH=backend python backend/scripts/hotpost/community_pool_feedback_dry_run.py \
  --input reports/community-governance/community-discovery-audit-<date>.json \
  --json-output reports/community-governance/community-pool-feedback-dry-run-<date>.json \
  --md-output reports/community-governance/community-pool-feedback-dry-run-<date>.md
```

人工只重点看：

- `pool_candidate`：进入 R12 预审
- `validated`：继续观察，不写池
- `testing`：继续补证据
- `already_in_pool`：不新增，只补证据
- `observe / no_signal_yet`：不动作

### 5. 用户确认后生成 R12 预写入审计

```bash
PYTHONPATH=backend python backend/scripts/hotpost/community_pool_r12_prewrite.py \
  --input reports/community-governance/community-pool-feedback-dry-run-<date>.json \
  --json-output reports/community-governance/community-pool-r12-prewrite-<date>.json \
  --md-output reports/community-governance/community-pool-r12-prewrite-<date>.md
```

R12 预审只回答四件事：

- 哪些社区会写入 Dev
- 哪些已存在所以跳过
- 哪些被阻断
- 标签映射是否需要人工复核

当前 R12 预审仍是 `writes_db=false`。

### 6. Dev 写入必须单独确认

只有同时满足以下条件，才允许进入真实 Dev 写入任务：

- R12 预审 `blocked=0`
- 用户明确确认写入
- 写入目标是 `reddit_signal_scanner_dev`
- 写入脚本有 DB guard
- 写入后生成 rollback SQL
- 写入后重跑社区推荐 preview / audit

没有这些条件，禁止手写 SQL，禁止借旧 Phase 2 写入脚本强写。

确认后先 dry-run：

```bash
PYTHONPATH=backend python backend/scripts/hotpost/community_pool_r12_dev_write.py \
  --input reports/community-governance/community-pool-r12-prewrite-<date>.json \
  --json-output reports/community-governance/community-pool-r12-dev-write-<date>.json \
  --md-output reports/community-governance/community-pool-r12-dev-write-<date>.md \
  --rollback-sql reports/community-governance/community-pool-r12-dev-write-rollback-<date>.sql
```

用户确认后再加 `--execute`。写入后必须重跑：

```bash
PYTHONPATH=backend python backend/scripts/community/community_recommendation_preview.py
```

## 每日报告模板

```text
今日探索社区回流：

- probe scope:
- audit report:
- R11.5:
  - input_rows:
  - already_in_pool:
  - promote_candidate:
  - keep_testing:
  - reject:
- pool_candidate:
  - r/xxx -> 标签 / score / evidence
- R12 prewrite:
  - candidate_rows:
  - would_insert:
  - skipped_existing:
  - blocked:
- R12 Dev write:
  - DB writes:
  - target_database:
  - active_count_before:
  - active_count_after:
  - inserted:
- 下一步：等待用户确认 / 继续观察 / 进入 Dev 写入准备
```

## 2026-05-10 当前样例

- R11.5：`input_rows=16 / already_in_pool=5 / promote_candidate=3 / keep_testing=8 / reject=0`
- R12 预审：`candidate_rows=3 / would_insert=3 / skipped_existing=0 / blocked=0`
- 本轮候选：
  - `r/aeo`
  - `r/ai_ugc_marketing`
  - `r/growthhacking`
- R12 Dev 写入：`DB writes=true / target_database=reddit_signal_scanner_dev / active_count_before=356 / active_count_after=359 / inserted=3`
- rollback：`reports/community-governance/community-pool-r12-dev-write-rollback-2026-05-10.sql`
- 推荐刷新：`tags=9 / recommendations=68 / ready_count=33 / acceptance_passed=true`

## 禁止事项

- 禁止把“探索已触发”当成“发现了新价值社区”。
- 禁止把 `promote_candidate` 自动写入 `community_pool`。
- 禁止用 Hotpost 没出卡来否定旧 DB 社区。
- 禁止把小程序快照、cloud DB 或 release 派生产物当社区池真相源。
- 禁止在代码里写死社区名、用户标签名或特殊分支。
