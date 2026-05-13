# Design: 主项目借鉴小程序产品机制瘦身
Date: 2026-05-07
Branch: feat/hotpost-cluster-aware-recall

## Problem Statement

主项目当前的问题不是“分析不够浅”，而是“采集和分析链路默认太重”。用户输入一个问题后，系统容易直接进入重采集、补评论、语义、facts、完整报告这一整套链路，导致验证慢、故障面大、`analysis_engine.py` 继续像大总管。

小程序给主项目的启发不能是分析深度。小程序的分析本来就浅，不能拿来替代主项目的 Full A / facts / report 能力。

真正值得借鉴的是小程序背后的产品机制：

- 真相源和派生产物分开
- 状态分层：原料、工作区、正式资产、分发快照
- 发布前有 gate
- 前台只读稳定资产，不重新拉动重任务
- 展示增强放在边缘 adapter，不污染主链
- 回滚靠 release / snapshot 指针，不靠手修缓存

主项目瘦身的真实目标是：**保留深分析，但让重采集变成有证据缺口时才升级的动作；让主入口变薄，让每一步产物可检查、可回滚、可复用。**

## Premise Challenges

1. “借鉴小程序”不等于“把主项目做浅”。
   结论：主项目必须保留深分析能力；借的是发布机制、门禁、快照、只读前台，不借小程序的分析粒度。

2. “采集路线重”不一定要靠重写 crawler 解决。
   结论：第一刀应该先改变默认产品合同：先做数据就绪判断和缺口说明，只有缺口明确时才触发有预算的补采。

3. “瘦身”不等于“大规模拆文件”。
   结论：审计已证明报告链做过真实解耦。下一步应优先收 `analysis_engine.py` 里已经有 support 模块承接的重复逻辑，而不是重做已有 report/crawl 解耦。

4. “用户要完整报告”不等于“每次都从零采集”。
   结论：主项目应该像小程序读 release 一样，尽量读已有 truth-source / cache / facts snapshot；只有报告质量门显示证据不足时，再进入补采和深挖。

## Options Considered

| Option | What | Effort | Risk | Decision |
| --- | --- | ---: | --- | --- |
| A. 轻扫描产品化 | 新增一层像 hotpost 卡片一样的浅扫描结果 | M | High | 拒绝。会把主项目降级成小程序式浅分析，偏离用户纠正。 |
| B. 产品机制瘦身 | 保留深分析，借鉴小程序的状态分层、gate、snapshot、只读前台机制 | M | Low | 采用。能减重采集，同时保护主项目分析深度。 |
| C. 直接拆 `analysis_engine.py` | 不改产品合同，直接按函数体拆文件 | M/L | Medium | 延后。容易为了瘦文件而瘦，不能保证采集路线变轻。 |
| D. 大重构成统一发布平台 | 主项目、Hotpost、小程序统一 release 系统 | XL | High | 拒绝。当前根仓极脏，不适合大平台化。 |

## Chosen Direction

采用 Option B：**产品机制瘦身**。

### Borrow From Mini / Hotpost

| 小程序/Hotpost 机制 | 主项目借鉴方式 |
| --- | --- |
| `candidates -> drafts -> releases -> mini_snapshots` | `input intent -> readiness snapshot -> analysis artifact -> report artifact` |
| release 不可变，snapshot 只读 | 报告页只读 `canonical_report_json`，不在前端拼报告，不因展示触发分析 |
| gate 之后才 publish | 数据就绪和 facts 质量门之后才生成完整报告 |
| snapshot adapter 可补展示字段 | 前端展示增强只在 report adapter / payload builder 做，不回写分析主链 |
| 小程序不跑重任务 | 主项目前台不直接拉动重采集，重采集通过明确 remediation / outbox 进入后台 |
| 派生产物坏了就重推 | 报告展示坏了先回源修 artifact，不手改导出或缓存 |

### Do Not Borrow

- 不借小程序的浅分析深度。
- 不把主项目输出改成 hotpost 卡片。
- 不把人工 review/publish 硬搬到主项目报告链。
- 不让小程序或 Hotpost 的 release 数据成为主项目分析真相源。

## Target Mainline Contract

```text
Input intent
  -> readiness snapshot
  -> decision gate
     -> enough data: deep analysis
     -> not enough data: bounded remediation / backfill order
  -> analysis artifact
  -> report artifact / canonical_report_json
  -> frontend read-only report
```

### Stage 1: Readiness Snapshot

回答一个问题：当前 Dev DB / cache / community truth-source 是否足够支撑这次分析？

现有可用基础：

- `backend/app/services/analysis/analysis_readiness_support.py`
- `build_data_readiness_snapshot(...)`
- `run_sample_guard_check(...)`
- `build_insufficient_sample_artifacts(...)`

### Stage 2: Decision Gate

回答一个问题：现在应该继续深分析，还是先补数据？

现有可用基础：

- `analysis_blocked = insufficient_samples`
- `data_readiness`
- `facts_v2_quality`
- `schedule_auto_backfill_for_insufficient_samples(...)`
- remediation budget / outbox

### Stage 3: Deep Analysis

只有 gate 通过后，才继续走原来的深分析链。主项目深度保留，不改成浅扫描。

### Stage 4: Report Artifact

前端只读 `canonical_report_json`。当前 `ReportPage.tsx` 已经在缺失 `canonical_report_json` 时硬失败，这个方向是对的。

## First Engineering Slice

第一刀不新建产品形态，不改 UI，不新建 DB 表。

只做一件事：

**把 `analysis_engine.py` 里已经有 support 模块承接的 readiness / insufficient sample / remediation 私有逻辑，收回到对应 support 模块，保留薄 wrapper。**

理由：

- 这直接延续小程序/Hotpost 的“单一真相源”机制。
- 它不改变主项目分析深度。
- 它能降低 `analysis_engine.py` 对采集前置判断的直接持有。
- 现有测试已经覆盖 `analysis_readiness_support` 和 `analysis_remediation_support`，风险可控。

## Success Criteria

- `analysis_engine.py` 不再自己维护完整 readiness snapshot / insufficient sample artifact / auto backfill 细节，只保留薄委托。
- `analysis_readiness_support.py` 和 `analysis_remediation_support.py` 成为对应逻辑的单一真相源。
- 现有主线 smoke 继续通过：
  - backend analyze/report/analysis smoke
  - frontend report/input contract smoke
- 报告深度不下降：`facts_v2_quality`、`canonical_report_json`、report assembly 合同不变。
- 不碰 Hotpost 日运营、小程序子仓、mini snapshots、cloudfunctions data。

## Risks

1. 风险：把产品瘦身误做成浅分析新功能。
   缓解：第一刀只收已有 support 边界，不新建轻扫描 UI。

2. 风险：`analysis_engine.py` 里旧 wrapper 被测试 monkeypatch 依赖。
   缓解：保留原私有函数名作为薄委托，先不删除入口。

3. 风险：readiness support 的实现与 engine 旧实现数据源不完全一致。
   缓解：新增 engine delegation 测试，锁定输出字段和 session_factory 注入。

4. 风险：重采集仍然被自动触发太多。
   缓解：第一刀只整理边界；后续再单独审 `remediation budget / outbox` 的产品策略。

## NOT in Scope

- 不降低主项目分析深度。
- 不新增浅扫描页。
- 不重写 crawler。
- 不拆 `ReportService`。
- 不清理根仓 `1474` 条 dirty status。
- 不改 Hotpost 发布合同。
- 不改小程序产品态。

## Next Concrete Action

写一个最小实现计划：

1. 给 `analysis_engine.py` 的 readiness / insufficient sample / remediation wrapper 补委托测试。
2. 把 wrapper 改成调用 `analysis_readiness_support` / `analysis_remediation_support`。
3. 跑目标测试和主线 smoke。
4. 再决定是否进入第二刀：`run_analysis` 深分析阶段的 artifact / finalization 收口。
