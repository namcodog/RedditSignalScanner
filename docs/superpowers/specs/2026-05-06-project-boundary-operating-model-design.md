# Design: 主项目与 Hotpost 小程序边界治理
Date: 2026-05-06
Branch: feat/hotpost-cluster-aware-recall

## Problem Statement

当前仓库里同时存在两条重要工作线：

- RedditSignalScanner 主项目：Reddit 数据采集、社区池、语义标注、分析任务、报告生成、后台运营工具。
- Hotpost 小程序分支：把已经正式发布的 hotpost 卡片稳定同步到手机端，承接首页、详情、收藏、登录、积分等消费层体验。

真实问题不是“选主项目还是小程序”，而是要建立清晰边界：小程序必须继续每天运营出卡，不能丢；主项目也要能继续推进，不被小程序问题长期吞掉注意力。两者要相互增益，但不能互相污染。

## Reconnaissance Findings

- `hotpost-mini/hotpost-mini-app` 是独立 git 子项目；当前子仓库 `git status` 干净。主仓库当前有大量既有改动，不能把主仓库脏状态带进小程序。
- 小程序项目说明明确：小程序是正式发布后的消费面，不负责 Reddit 抓取、freshness gate、collect 配额、candidate / draft 工作区、发布数量决定或争议图生成。
- Hotpost 存储合同明确：`candidates` 是原料池，`drafts` 是工作区，`releases` 是正式资产，`mini_snapshots` 和 `cloudfunctions/*/data` 是派生产物，只能由 `push_mini_snapshot.py` 写入。
- 前端 Web 路由已经分开：
  - 主项目：`/`、`/progress/:taskId`、`/report/:taskId`、`/standard-report/:slug`、`/insights`、`/admin/...`
  - Hotpost Web 运营面：`/hotpost`、`/hotpost/clues/:clueId`、`/hotpost/box`、`/hotpost/lab/search`、`/hotpost/result/:queryId`
- 后端 API 是同一 FastAPI，但路由分层清楚：
  - 主项目：`analyze`、`tasks`、`stream`、`reports`、`export`、`decision_units`
  - Hotpost：`hotpost*`、`hotpost_wx_auth`、`hotpost_wx_favorites`
- phase-log 最新主线仍偏 `hotpost all-scope 日运营 / freshest supply`。如果要重新推进主项目，需要先把“主项目复位”作为新任务显式记录，不能静默覆盖日常出卡节奏。

## Premise Challenges

1. “小程序只是分支，所以可以先放一边”不成立。
   小程序是当前 hotpost 正式发布内容的消费面，每天出卡后必须同步和验收；它不是临时 demo。

2. “主项目和小程序完全分开”也不成立。
   小程序消费的是主仓 hotpost 正式 release 和 mini snapshot；内容供给、发布合同、快照同步都在主仓完成。

3. “回主项目就停止 hotpost”不成立。
   当前更合理的做法是双轨：主项目进入复位/推进轨，小程序和 hotpost 日运营保留固定节奏。

## Options Considered

| Option | What | Effort | Risk | Decision |
| --- | --- | --- | --- | --- |
| A. 单轨回主项目 | 暂停 hotpost/小程序，只恢复分析报告主链 | S | High | 拒绝。会破坏每天出卡和小程序运营连续性。 |
| B. 双轨边界治理 | 主项目推进和 hotpost 小程序运营分轨，每次任务先声明轨道和触碰范围 | M | Low | 采用。能保运营，也能恢复主项目。 |
| C. 全部重构成统一平台 | 重新设计主项目、hotpost、小程序的统一架构 | L | High | 拒绝。现在不是大架构重建期。 |

## Chosen Direction

采用 Option B：双轨边界治理。

### Track 1: 主项目轨

负责：

- RedditSignalScanner Web 主产品
- `community -> crawl -> semantic -> analyze -> report`
- Dev DB / Test DB / Gold DB 数据口径
- 分析报告、事实证据、导出、后台社区治理
- 相关目录：`backend/app/services/analysis`、`backend/app/services/report`、`backend/app/services/community`、`backend/app/services/crawl`、`backend/app/services/semantic`、`frontend/src/pages/InputPage.tsx`、`ReportPage.tsx`、`StandardReportPage.tsx`、`Admin*`

默认不碰：

- `hotpost-mini/hotpost-mini-app`
- `backend/data/hotpost/mini_snapshots`
- `hotpost-mini/.../cloudfunctions/*/data`
- 日常出卡的 candidates / drafts / releases，除非任务明确需要。

### Track 2: Hotpost 日运营轨

负责：

- 每天 `all-scope` 出卡
- `collect -> sync -> plan -> gate -> review/publish`
- V13 出卡链路
- release / mini snapshot / cloud db / miniRelease 同步
- 运营日志和 phase-log 的发布结果记录

硬规则：

- 每天运营不能被主项目推进吞掉。
- 出卡后必须继续跑 `push_mini_snapshot.py`、`check_mini_release_sync.py`、`npm run check:mini-snapshot-data`。
- `mini_snapshots` 和云函数 data 不能手改。
- 小程序功能改动必须先锁产品态基线，再做单变量验证。

### Track 3: 小程序产品轨

负责：

- Taro 小程序源码、页面体验、云函数、真机表现
- 目录只限：`hotpost-mini/hotpost-mini-app`
- 发布派生产物只通过主仓 `push_mini_snapshot.py` 更新

默认不碰：

- 主项目分析/报告链
- hotpost candidate / draft / release 决策
- 后端 freshness gate 和出卡质量门

## Operating Rules

1. 每次开工先声明轨道：主项目轨、Hotpost 日运营轨、小程序产品轨，或明确的跨轨任务。
2. 跨轨任务必须写清楚“谁是真相源，谁是派生产物”。
3. 主项目任务默认不进入小程序子仓；小程序任务默认不回推主仓大范围改动。
4. 日常出卡是固定运营节奏，不能因为主项目开发被取消；最多调整当天执行窗口。
5. 如果主项目改动会影响 hotpost API、release、snapshot 或小程序读取，必须先列兼容性检查。
6. 如果小程序体验改动会影响已验收产品态，先读 `.product-baseline.json` 和 `docs/product-baseline.md`，再做单变量修改。
7. 主仓当前有大量既有改动；任何新改动都必须只碰当前任务需要的文件，不整理无关 diff。
8. 不同轨道必须使用不同 plan 文件：日常出卡继续用根目录 `task_plan.md`；边界护栏、主项目复位、小程序功能各自放在 `docs/superpowers/plans/`，不能混写。
9. 提交前必须运行 `make boundary-status`；主项目提交不得包含小程序子仓改动，小程序提交必须在子仓内完成。

## Success Criteria

- 能一句话判断当前任务属于哪条轨。
- 主项目复位时，不破坏每天出卡、release、snapshot、小程序同步。
- 小程序修复时，不顺手改变 hotpost 供给、发布门禁、V13 prompt 或主项目分析链。
- 每天出卡后仍能稳定得到最新 release、mini snapshot、cloud db bundle 和运营日志。
- 主项目推进能重新跑通至少一条 `analyze -> progress -> report` 验收链。

## Risks

1. 风险：主仓 hotpost 和小程序共享派生产物，容易误手改缓存。
   缓解：派生产物只由 `push_mini_snapshot.py` 写入；人工只改真相源。

2. 风险：主项目复位时被 hotpost 当前节奏打断。
   缓解：把日常运营固定成每日窗口；主项目任务只在窗口外推进，或先完成当天出卡最小闭环。

3. 风险：phase-log 当前状态仍偏 hotpost，后续接手人看不出双轨。
   缓解：用户确认后，更新 `CURRENT_STATUS / OPEN_ITEMS / INDEX`，但不新增流水 phase，除非主线优先级正式变化。

## NOT in Scope

- 不暂停 Hotpost 日常运营。
- 不重构小程序架构。
- 不改 V13 出卡链路。
- 不改 hotpost storage contract。
- 不处理主仓现有大量无关 dirty diff。
- 不直接修主项目 analyze/report 代码；下一步先做复位审计和验收。

## Next Concrete Action

先做一次主项目复位审计，但不影响当天出卡：

1. 核实主项目 `analyze -> progress -> report` 的后端和前端测试现状。
2. 核实 Dev DB / Test DB / Gold DB 使用口径有没有被近期 hotpost 工作污染。
3. 列出主项目当前最短可验收链路。
4. 单独保留 Hotpost 日运营 checklist，确保每天出卡和小程序同步不断档。
